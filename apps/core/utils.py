"""
Utilitários do app core.

Funções auxiliares para notificações e outras funcionalidades gerais.
"""


def criar_notificacao(usuario_destino, motivo_codigo, texto, link_destino, usuario_origem=None):
    """
    Cria uma notificação e gerencia limite de notificações do usuário.

    Args:
        usuario_destino (User): Usuário que receberá a notificação
        motivo_codigo (str): Código do MotivoNotificacao (ex: 'MENCAO_COMENTARIO')
        texto (str): Texto da notificação
        link_destino (str): URL de destino
        usuario_origem (User, optional): Usuário que gerou a notificação

    Returns:
        Notificacao: Objeto criado

    Raises:
        MotivoNotificacao.DoesNotExist: Se motivo não existe ou está inativo

    Example:
        >>> from django.contrib.auth import get_user_model
        >>> User = get_user_model()
        >>> usuario = User.objects.get(username='joao')
        >>> autor = User.objects.get(username='maria')
        >>> criar_notificacao(
        ...     usuario_destino=usuario,
        ...     motivo_codigo='MENCAO_COMENTARIO',
        ...     texto='@maria marcou você em um comentário.',
        ...     link_destino='/texto/123/',
        ...     usuario_origem=autor
        ... )
    """
    from apps.core.models import MotivoNotificacao, Notificacao

    # Buscar motivo ativo
    motivo = MotivoNotificacao.objects.get(codigo=motivo_codigo, ativo=True)

    # Criar notificação
    notificacao = Notificacao.objects.create(
        motivo=motivo,
        usuario_origem=usuario_origem,
        usuario_destino=usuario_destino,
        texto=texto,
        link_destino=link_destino
    )

    # Gerenciar limite de notificações
    _limpar_notificacoes_antigas(usuario_destino)

    return notificacao


def _limpar_notificacoes_antigas(usuario):
    """
    Remove notificações antigas excedendo o limite configurado pelo usuário.

    Mantém apenas as N notificações mais recentes (padrão: 50).
    As notificações são ordenadas por data de criação (mais recentes primeiro).

    Args:
        usuario (User): Usuário cujas notificações serão limpas

    Example:
        Se usuário tem 55 notificações, as 5 mais antigas serão deletadas.
    """
    from apps.core.models import Notificacao

    # Usar limite padrão de 50 notificações (pode ser configurável no futuro)
    limite = getattr(usuario.configuracao, 'limite_notificacoes', 50)
    notificacoes = Notificacao.objects.filter(
        usuario_destino=usuario
    ).order_by('-data_criacao')

    total = notificacoes.count()

    if total > limite:
        # Pegar IDs das notificações a serem deletadas (mais antigas)
        ids_deletar = list(notificacoes.values_list('id', flat=True)[limite:])
        Notificacao.objects.filter(id__in=ids_deletar).delete()


def extrair_primeiras_frases(texto_html, num_frases=2):
    """
    Extrai as primeiras N frases de um conteúdo HTML.

    Remove tags HTML e retorna as primeiras frases do texto puro,
    finalizando com "..." para indicar continuação.

    Args:
        texto_html (str): Conteúdo HTML do texto
        num_frases (int): Número de frases a extrair (padrão: 2)

    Returns:
        str: Primeiras frases do texto seguidas de "(...)"

    Example:
        >>> html = "<p>Esta é a primeira frase. Esta é a segunda! E esta a terceira.</p>"
        >>> extrair_primeiras_frases(html, 2)
        'Esta é a primeira frase. Esta é a segunda! (...)'
    """
    import re
    from html import unescape

    if not texto_html:
        return ""

    # Remover tags HTML
    texto_limpo = re.sub(r'<[^>]+>', ' ', texto_html)

    # Decodificar entidades HTML (&nbsp;, &amp;, etc.)
    texto_limpo = unescape(texto_limpo)

    # Normalizar espaços (múltiplos espaços -> um espaço)
    texto_limpo = re.sub(r'\s+', ' ', texto_limpo).strip()

    if not texto_limpo:
        return ""

    # Encontrar frases usando delimitadores de fim de sentença (.!?)
    # Padrão: captura texto até pontuação final, incluindo a pontuação
    padrao_frases = re.findall(r'[^.!?]*[.!?]', texto_limpo)

    if not padrao_frases:
        # Se não encontrou frases com pontuação, retorna o texto limitado
        if len(texto_limpo) > 200:
            return texto_limpo[:200].strip() + ' (...)'
        return texto_limpo

    # Pegar as primeiras N frases
    frases_selecionadas = padrao_frases[:num_frases]

    # Juntar e limpar
    trecho = ''.join(frases_selecionadas).strip()

    # Adicionar indicador de continuação se houver mais texto
    if len(padrao_frases) > num_frases or len(texto_limpo) > len(trecho):
        trecho += ' (...)'

    return trecho


def notificar_seguidores_novo_texto(texto):
    """
    Notifica todos os seguidores do autor sobre publicação de novo texto.

    Item 3 do ROADMAP - Notificações de publicação por e-mail:
    Quando um autor publica um texto, esta função:
    1. Cria notificações na tabela Notificacao para TODOS os seguidores
    2. Envia e-mail APENAS para seguidores que optaram por receber (receber_email_autores_favoritos=True)

    Args:
        texto (Texto): Objeto Texto recém-publicado

    Returns:
        dict: Estatísticas das notificações enviadas
            - total_seguidores: Total de seguidores do autor
            - notificacoes_criadas: Total de notificações criadas no banco
            - emails_enviados: Total de e-mails enviados com sucesso
            - emails_falhados: Total de e-mails que falharam

    Example:
        >>> from apps.textos.models import Texto
        >>> texto = Texto.objects.get(pk=123)
        >>> estatisticas = notificar_seguidores_novo_texto(texto)
        >>> print(f"Notificações: {estatisticas['notificacoes_criadas']}, E-mails: {estatisticas['emails_enviados']}")
    """
    from apps.usuarios.models import AutorSeguido
    from apps.core.models import MotivoNotificacao
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.conf import settings
    from django.urls import reverse

    # Inicializar estatísticas
    estatisticas = {
        'total_seguidores': 0,
        'notificacoes_criadas': 0,
        'emails_enviados': 0,
        'emails_falhados': 0
    }

    # Buscar ou criar motivo de notificação
    motivo, _ = MotivoNotificacao.objects.get_or_create(
        codigo='NOVO_TEXTO_AUTOR',
        defaults={
            'nome': 'Novo texto de autor seguido',
            'descricao': 'Notificação enviada quando um autor que o usuário segue publica um novo texto',
            'ativo': True
        }
    )

    # Se motivo está inativo, não notificar
    if not motivo.ativo:
        return estatisticas

    # Buscar todos os seguidores do autor
    seguidores = AutorSeguido.objects.filter(
        autor=texto.autor
    ).select_related('seguidor', 'seguidor__configuracao')

    estatisticas['total_seguidores'] = seguidores.count()

    # Determinar nome do autor baseado no display_autoria do texto
    from apps.textos.models import Texto

    if texto.display_autoria == Texto.DisplayAutoria.PSEUDONIMO:
        nome_autor = texto.autor.pseudonimo or texto.autor.get_full_name()
    elif texto.display_autoria == Texto.DisplayAutoria.AMBOS:
        nome_completo = texto.autor.get_full_name()
        pseudonimo = texto.autor.pseudonimo
        nome_autor = f"{nome_completo} ({pseudonimo})" if pseudonimo else nome_completo
    else:  # REAL
        nome_autor = texto.autor.get_full_name()

    # URL absoluta do texto para o e-mail
    link_texto_absoluto = f"https://livredia.com.br{reverse('textos:leitura_texto', kwargs={'pk': texto.pk})}"

    # URL absoluta das configurações
    link_configuracoes_absoluto = f"https://livredia.com.br{reverse('usuarios:configuracoes')}"

    # Extrair trecho do texto (primeiras 2 frases)
    trecho_texto = extrair_primeiras_frases(texto.conteudo, num_frases=2)

    # Para cada seguidor
    for autor_seguido in seguidores:
        seguidor = autor_seguido.seguidor

        # Link relativo do texto (para notificação)
        link_texto = reverse('textos:leitura_texto', kwargs={'pk': texto.pk})

        # Texto da notificação
        texto_notificacao = f'{nome_autor} que você segue publicou um novo texto! Confira aqui!'

        # Criar notificação no banco (para TODOS os seguidores)
        try:
            criar_notificacao(
                usuario_destino=seguidor,
                motivo_codigo='NOVO_TEXTO_AUTOR',
                texto=texto_notificacao,
                link_destino=link_texto,
                usuario_origem=texto.autor
            )
            estatisticas['notificacoes_criadas'] += 1
        except Exception as e:
            # Log do erro (não interromper o loop)
            print(f"Erro ao criar notificação para {seguidor.username}: {str(e)}")

        # Verificar se seguidor optou por receber e-mail
        try:
            configuracao = seguidor.configuracao
            receber_email = configuracao.receber_email_autores_favoritos
        except:
            # Se não tem configuração (improvável), não enviar e-mail
            receber_email = False

        # Enviar e-mail APENAS se seguidor optou por receber
        if receber_email:
            try:
                # Renderizar template HTML
                html_content = render_to_string('emails/notificacao_novo_texto.html', {
                    'nome_seguidor': seguidor.get_full_name(),
                    'nome_autor': nome_autor,
                    'titulo_texto': texto.titulo,
                    'subtitulo_texto': texto.subtitulo,
                    'trecho_texto': trecho_texto,
                    'link_texto': link_texto_absoluto,
                    'link_configuracoes': link_configuracoes_absoluto,
                })

                # Assunto do e-mail
                assunto = f'{nome_autor} publicou um novo texto no Livre Dia'

                # Enviar e-mail
                send_mail(
                    subject=assunto,
                    message='',  # Versão em texto puro (vazia, usaremos apenas HTML)
                    from_email=f'Livre Dia <{settings.DEFAULT_FROM_EMAIL}>',
                    recipient_list=[seguidor.email],
                    html_message=html_content,
                    fail_silently=False,  # Lançar exceção se falhar
                )

                estatisticas['emails_enviados'] += 1

            except Exception as e:
                # Log do erro (não interromper o loop)
                print(f"Erro ao enviar e-mail para {seguidor.email}: {str(e)}")
                estatisticas['emails_falhados'] += 1

    return estatisticas


def enviar_email_convite_autor(convite, autor_convidante, request=None):
    """
    Envia e-mail de convite para um novo autor.

    Quando um autor convida outro autor para a plataforma, esta função
    envia o e-mail de boas-vindas com o link de ativação.

    Args:
        convite (ConviteAutor): Objeto ConviteAutor com o token de ativação
        autor_convidante (User): Usuário autor que está fazendo o convite
        request (HttpRequest, optional): Request para construir URL absoluta

    Returns:
        bool: True se e-mail foi enviado com sucesso, False caso contrário
    """
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.conf import settings

    try:
        # Obter link de ativação
        link_ativacao = convite.get_link_ativacao(request)

        # Dados do novo autor (convidado)
        novo_autor = convite.autor
        nome_convidado = novo_autor.get_full_name() or novo_autor.email

        # Nome do autor que está convidando
        nome_convidante = autor_convidante.get_full_name() or autor_convidante.username

        # Renderizar template HTML do e-mail
        html_content = render_to_string('emails/convite_autor.html', {
            'nome': nome_convidado,
            'autor_convidante': nome_convidante,
            'link_ativacao': link_ativacao,
            'sexo': novo_autor.sexo,  # Para flexão de gênero no e-mail
        })

        # Assunto do e-mail
        assunto = f'Convite para escrever no LIVRE DIA - {nome_convidante} te convidou!'

        # Enviar e-mail
        send_mail(
            subject=assunto,
            message='',  # Versão em texto puro (vazia, usaremos apenas HTML)
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[novo_autor.email],
            html_message=html_content,
            fail_silently=False,
        )

        return True

    except Exception as e:
        print(f"Erro ao enviar e-mail de convite para {convite.autor.email}: {str(e)}")
        return False
