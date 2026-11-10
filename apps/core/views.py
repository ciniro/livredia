from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView, DetailView, FormView
from django.urls import reverse_lazy
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Count
from .models import PaginaEstatica
from .forms import FaleConoscoForm


class HomeView(TemplateView):
    """
    View da página inicial (Home).

    Tela 7 - FASE 2: ZONA PÚBLICA - CONTEÚDO
    Baseada no protótipo: prototipos_telas/home_(página_inicial)/code.html

    Exibe:
    - Bloco hero com propósito da plataforma (PaginaEstatica)
    - Autores mais lidos (sidebar com 6 autores em grid 2x3)
    - Últimos textos publicados (grid com 12 textos)
    - Categorias de texto (tags mais usadas)
    """
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        """Carrega todos os dados necessários para a home."""
        from apps.usuarios.models import User, AutorSeguido
        from apps.textos.models import Texto, Tag, TextoLeituraPosterior
        from django.db.models import Sum, Exists, OuterRef, Value

        context = super().get_context_data(**kwargs)

        # 1. Página estática com o propósito/hero
        try:
            context['pagina_proposito'] = PaginaEstatica.objects.get(slug='home-proposito')
        except PaginaEstatica.DoesNotExist:
            context['pagina_proposito'] = None

        # 2. Autores mais vistos (6 autores com mais visualizações nos textos)
        # Conta o total de visualizações de todos os textos de cada autor
        # IMPORTANTE: Exclui autores suspensos (is_suspended=False)
        from django.db.models import Q, Case, When, IntegerField

        autores_vistos = User.objects.filter(
            role=User.Role.AUTOR,
            is_active=True,
            is_suspended=False,  # Ocultar autores suspensos
            textos__status=Texto.Status.PUBLICADO  # Apenas textos publicados
        ).annotate(
            total_visualizacoes=Count('textos__visualizacoes'),
            # Conta quantos textos usam pseudônimo (display_autoria=PSEUDONIMO ou AMBOS)
            textos_com_pseudonimo=Count(
                'textos',
                filter=Q(
                    textos__status=Texto.Status.PUBLICADO,
                    textos__display_autoria__in=[Texto.DisplayAutoria.PSEUDONIMO, Texto.DisplayAutoria.AMBOS]
                )
            )
        ).filter(
            total_visualizacoes__gt=0  # Apenas autores com pelo menos 1 visualização
        ).order_by('-total_visualizacoes')[:6]

        # Adicionar flag para indicar se deve usar filtro de pseudônimo
        for autor in autores_vistos:
            # Se tem pseudônimo E tem textos usando pseudônimo, usar filtro de pseudônimo
            autor.usar_filtro_pseudonimo = (
                bool(autor.pseudonimo) and
                autor.textos_com_pseudonimo > 0
            )

        context['autores_mais_vistos'] = autores_vistos

        # 3. Últimos textos publicados (12 mais recentes, ordenados por data/hora)
        # IMPORTANTE: Exclui textos de autores suspensos E textos suspensos
        ultimos_textos = Texto.objects.filter(
            status=Texto.Status.PUBLICADO,
            is_suspended=False,  # Ocultar textos suspensos
            autor__is_suspended=False  # Ocultar textos de autores suspensos
        ).select_related('autor').prefetch_related('tags').order_by('-data_publicacao')[:12]

        # Anotar se o usuário logado salvou cada texto para ler mais tarde (Item 4.1 do ROADMAP)
        # e se está seguindo o autor
        if self.request.user.is_authenticated:
            ultimos_textos = ultimos_textos.annotate(
                na_lista_leitura=Exists(
                    TextoLeituraPosterior.objects.filter(
                        usuario=self.request.user,
                        texto=OuterRef('pk')
                    )
                ),
                seguindo_autor=Exists(
                    AutorSeguido.objects.filter(
                        seguidor=self.request.user,
                        autor=OuterRef('autor')
                    )
                )
            )
        else:
            ultimos_textos = ultimos_textos.annotate(
                na_lista_leitura=Value(False),
                seguindo_autor=Value(False)
            )

        context['ultimos_textos'] = ultimos_textos

        # 4. Tags mais usadas (categorias de texto) - aumentado para mostrar mais tags (3+ linhas)
        context['tags_populares'] = Tag.objects.annotate(
            num_textos=Count('textos')
        ).filter(num_textos__gt=0).order_by('-num_textos')[:40]

        # 5. Autores mais lidos (top 6) - Item 12.3(b)
        # Soma o tempo_permanencia de todas as visualizações dos textos de cada autor
        autores_lidos = User.objects.filter(
            role=User.Role.AUTOR,
            is_active=True,
            is_suspended=False,
            textos__status=Texto.Status.PUBLICADO
        ).annotate(
            total_tempo=Sum('textos__visualizacoes__tempo_permanencia'),
            textos_com_pseudonimo=Count(
                'textos',
                filter=Q(
                    textos__status=Texto.Status.PUBLICADO,
                    textos__display_autoria__in=[Texto.DisplayAutoria.PSEUDONIMO, Texto.DisplayAutoria.AMBOS]
                )
            )
        ).filter(
            total_tempo__gt=0
        ).order_by('-total_tempo')[:6]

        # Adicionar flag de pseudônimo
        for autor in autores_lidos:
            autor.usar_filtro_pseudonimo = (
                bool(autor.pseudonimo) and
                autor.textos_com_pseudonimo > 0
            )

        context['autores_mais_lidos'] = autores_lidos

        # 6. Textos mais vistos (top 5) - Item 12.3(c)
        # Conta o total de visualizações de cada texto
        textos_mais_vistos = Texto.objects.filter(
            status=Texto.Status.PUBLICADO,
            is_suspended=False,
            autor__is_suspended=False
        ).annotate(
            total_visualizacoes=Count('visualizacoes')
        ).filter(
            total_visualizacoes__gt=0
        ).select_related('autor').prefetch_related('tags').order_by('-total_visualizacoes')[:5]

        # Anotar se o usuário logado salvou cada texto para ler mais tarde (Item 4.1 do ROADMAP)
        if self.request.user.is_authenticated:
            textos_mais_vistos = textos_mais_vistos.annotate(
                na_lista_leitura=Exists(
                    TextoLeituraPosterior.objects.filter(
                        usuario=self.request.user,
                        texto=OuterRef('pk')
                    )
                )
            )
        else:
            textos_mais_vistos = textos_mais_vistos.annotate(na_lista_leitura=Value(False))

        context['textos_mais_vistos'] = textos_mais_vistos

        # 7. Textos mais lidos (top 5) - Item 12.3(d)
        # Soma o tempo_permanencia de todas as visualizações de cada texto
        textos_mais_lidos = Texto.objects.filter(
            status=Texto.Status.PUBLICADO,
            is_suspended=False,
            autor__is_suspended=False
        ).annotate(
            total_tempo=Sum('visualizacoes__tempo_permanencia')
        ).filter(
            total_tempo__gt=0
        ).select_related('autor').prefetch_related('tags').order_by('-total_tempo')[:5]

        # Anotar se o usuário logado salvou cada texto para ler mais tarde (Item 4.1 do ROADMAP)
        if self.request.user.is_authenticated:
            textos_mais_lidos = textos_mais_lidos.annotate(
                na_lista_leitura=Exists(
                    TextoLeituraPosterior.objects.filter(
                        usuario=self.request.user,
                        texto=OuterRef('pk')
                    )
                )
            )
        else:
            textos_mais_lidos = textos_mais_lidos.annotate(na_lista_leitura=Value(False))

        context['textos_mais_lidos'] = textos_mais_lidos

        return context


class PaginaEstaticaView(DetailView):
    """
    View genérica para páginas estáticas do CMS.

    Usada para: Manifesto, Quem Somos, Selo Livre de IA.
    Busca PaginaEstatica pelo slug e renderiza o conteúdo.

    Uso:
        - /manifesto/ → slug='manifesto'
        - /quem-somos/ → slug='quem-somos'
        - /selo-livre-de-ia/ → slug='selo-livre-de-ia'
    """
    model = PaginaEstatica
    template_name = 'core/pagina_estatica.html'
    context_object_name = 'pagina'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'


class FaleConoscoView(FormView):
    """
    View de formulário de contato público.

    Permite que visitantes enviem mensagens para o admin.
    Em form_valid(), envia email e exibe mensagem de sucesso.

    Baseado no protótipo HTML em prototipos_telas/página_fale_conosco/
    """
    template_name = 'core/fale_conosco.html'
    form_class = FaleConoscoForm
    success_url = reverse_lazy('core:fale_conosco')

    def form_valid(self, form):
        """
        Processa o formulário válido:
        1. Extrai os dados
        2. Busca contatos administrativos ativos
        3. Envia email HTML para todos eles
        4. Exibe mensagem de sucesso
        """
        from apps.painel_admin.models import ContatoAdministrativo
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string

        nome = form.cleaned_data['nome']
        email = form.cleaned_data['email']
        assunto = form.cleaned_data['assunto']
        mensagem = form.cleaned_data['mensagem']

        # Buscar contatos administrativos ativos
        contatos = ContatoAdministrativo.objects.filter(
            ativo=True
        ).values_list('email', flat=True)

        # Fallback: se nenhum contato ativo, usar CONTACT_EMAIL
        recipient_list = list(contatos) if contatos.exists() else [settings.CONTACT_EMAIL]

        # Debug: imprimir destinatários
        print(f'[DEBUG] Enviando email para {len(recipient_list)} destinatário(s): {recipient_list}')

        # Renderizar template HTML do email
        contexto_email = {
            'nome': nome,
            'email': email,
            'assunto': assunto,
            'mensagem': mensagem,
        }

        html_content = render_to_string('emails/contato_formulario.html', contexto_email)

        # Versão texto plano (fallback)
        texto_plano = f"""
Nova mensagem de contato recebida via LIVRE DIA

De: {nome} ({email})
Assunto: {assunto}

Mensagem:
{mensagem}

---
Este e-mail foi enviado por um usuário do LIVRE DIA através do Fale Conosco. Para responder use o e-mail informado pelo usuário.
"""

        try:
            # Enviar email HTML - usando BCC para múltiplos destinatários
            email_msg = EmailMultiAlternatives(
                subject=f'[LIVRE DIA] {assunto}',
                body=texto_plano,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_list[0]],  # Primeiro destinatário no TO
                bcc=recipient_list[1:] if len(recipient_list) > 1 else [],  # Demais no BCC
                reply_to=[email]  # Permite responder diretamente ao remetente
            )
            email_msg.attach_alternative(html_content, "text/html")
            email_msg.send(fail_silently=False)

            print(f'[DEBUG] Email enviado com sucesso para {len(recipient_list)} destinatário(s)')

            messages.success(
                self.request,
                f'Obrigado, {nome}! Sua mensagem foi enviada com sucesso. '
                'Responderemos em breve no email fornecido.'
            )
        except Exception as e:
            # Se houver erro no envio de email, registrar mas não falhar
            messages.warning(
                self.request,
                f'Obrigado, {nome}! Sua mensagem foi registrada. '
                'Caso não receba resposta em 48h, tente novamente.'
            )
            print(f'Erro ao enviar email de contato: {e}')

        return super().form_valid(form)

    def form_invalid(self, form):
        """Exibe mensagem de erro se o formulário for inválido."""
        messages.error(
            self.request,
            'Houve um erro no formulário. Por favor, corrija os campos destacados.'
        )
        return super().form_invalid(form)


# ===========================
# NOTIFICAÇÕES (Item 5.1 do ROADMAP)
# ===========================

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json


@login_required
@require_http_methods(["GET"])
def listar_notificacoes_nao_lidas(request):
    """
    Lista notificações não lidas do usuário logado.

    Retorna JSON com lista de notificações ordenadas por data (mais recentes primeiro).

    Returns:
        JsonResponse: {
            "notificacoes": [
                {
                    "id": 1,
                    "texto": "...",
                    "link_destino": "...",
                    "data_criacao": "..."
                },
                ...
            ]
        }
    """
    from .models import Notificacao

    # Buscar até 11 notificações para saber se há mais do que 10
    notificacoes = Notificacao.objects.filter(
        usuario_destino=request.user,
        lida=False
    ).select_related('motivo', 'usuario_origem').order_by('-data_criacao')[:11]

    # Verificar se há mais de 10 notificações
    tem_mais = len(notificacoes) > 10
    notificacoes_limitadas = list(notificacoes)[:10]  # Limitar a 10

    # Serializar notificações
    notificacoes_data = []
    for notif in notificacoes_limitadas:
        # URL do perfil do usuário de origem (se existir)
        usuario_origem_perfil = f'/@{notif.usuario_origem.username}' if notif.usuario_origem else None

        notificacoes_data.append({
            'id': notif.id,
            'texto': notif.texto,
            'link_destino': notif.link_destino,
            'data_criacao': notif.data_criacao.isoformat(),
            'motivo': notif.motivo.nome if notif.motivo else '',
            'usuario_origem_avatar': notif.usuario_origem.get_avatar_url() if notif.usuario_origem else None,
            'usuario_origem_nome': notif.usuario_origem.get_display_name() if notif.usuario_origem else 'Sistema',
            'usuario_origem_perfil': usuario_origem_perfil,
        })

    return JsonResponse({
        'notificacoes': notificacoes_data,
        'tem_mais': tem_mais
    })


@login_required
@require_http_methods(["POST"])
def marcar_notificacao_como_lida(request, notificacao_id):
    """
    Marca UMA notificação específica como lida.

    Chamado quando o usuário clica em uma notificação no dropdown.

    Args:
        notificacao_id: ID da notificação a ser marcada como lida

    Returns:
        JsonResponse: {"success": True} ou {"success": False, "error": "..."}
    """
    from .models import Notificacao

    try:
        # Buscar notificação e verificar se pertence ao usuário
        notificacao = Notificacao.objects.get(
            id=notificacao_id,
            usuario_destino=request.user
        )

        # Marcar como lida
        notificacao.lida = True
        notificacao.save()

        return JsonResponse({'success': True})

    except Notificacao.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Notificação não encontrada'
        }, status=404)


# ===========================
# REDE DE CONVITES (Página Pública)
# ===========================

def rede_convites_view(request):
    """
    View da página pública "Rede de Convites".

    Exibe:
    - Texto institucional explicando o sistema de curadoria por convites
    - Árvore visual de convites mostrando a rede de autores

    A árvore é construída a partir dos registros de ConviteAutor onde
    convidado_por não é nulo, indicando que um autor convidou outro.

    IMPORTANTE (Item 4 ROADMAP):
    - Autores clássicos (is_classico=True) NUNCA aparecem na árvore
    - Autores fundadores (contemporâneos sem convite) aparecem como raízes independentes
    """
    from apps.painel_admin.models import ConviteAutor
    from apps.usuarios.models import User

    # === LÓGICA DO ITEM 4 ROADMAP ===
    # 1. Mostrar APENAS autores contemporâneos (is_classico=False) na árvore
    # 2. Fundadores = contemporâneos que:
    #    a) Não têm registro na tabela ConviteAutor, OU
    #    b) Têm registro mas convidado_por é NULL (admin), OU
    #    c) Têm registro mas convidado_por é clássico
    # 3. Clássicos NUNCA aparecem na árvore

    # Todos os autores contemporâneos ativos
    todos_contemporaneos = User.objects.filter(
        role='AUTOR',
        is_active=True,
        is_classico=False
    )

    # Buscar convites onde AMBOS são contemporâneos (conexões válidas da árvore)
    convites_entre_contemporaneos = ConviteAutor.objects.filter(
        ativado=True,
        convidado_por__isnull=False,
        autor__is_classico=False,  # Convidado é contemporâneo
        convidado_por__is_classico=False  # Convidante é contemporâneo
    ).select_related('autor', 'convidado_por').order_by('data_criacao')

    # IDs de contemporâneos que foram convidados por outros contemporâneos
    convidados_por_contemporaneos = set(c.autor_id for c in convites_entre_contemporaneos)

    # Fundadores = contemporâneos que NÃO foram convidados por outro contemporâneo
    # (inclui: sem registro, convidado por admin, convidado por clássico)
    fundadores = todos_contemporaneos.exclude(id__in=convidados_por_contemporaneos)

    # Estatísticas gerais (apenas autores contemporâneos ativos)
    total_autores = todos_contemporaneos.count()
    total_convites_ativados = convites_entre_contemporaneos.count()

    # Raízes da árvore = fundadores
    raizes = fundadores

    # Construir dicionário de convites para facilitar navegação
    convites_por_convidante = {}
    for convite in convites_entre_contemporaneos:
        if convite.convidado_por_id not in convites_por_convidante:
            convites_por_convidante[convite.convidado_por_id] = []
        convites_por_convidante[convite.convidado_por_id].append(convite)

    # Função recursiva para construir árvore
    def construir_arvore(autor, nivel=0, data_convite=None):
        """Constrói nó da árvore com filhos recursivamente."""
        convites_do_autor = convites_por_convidante.get(autor.id, [])

        # Ordenar por data de criação
        convites_do_autor.sort(key=lambda c: c.data_criacao)

        filhos = []
        for convite in convites_do_autor:
            # Passa a data do convite para o filho
            filhos.append(construir_arvore(convite.autor, nivel + 1, convite.data_criacao))

        return {
            'id': autor.id,
            'username': autor.username,
            'nome': autor.pseudonimo or autor.first_name or autor.username,
            'foto': autor.foto.url if autor.foto else None,
            'nivel': nivel,
            'filhos': filhos,
            'total_filhos': len(filhos),
            'data_convite': data_convite.strftime('%d/%m/%Y') if data_convite else None,
        }

    # Construir árvores a partir de cada raiz
    arvores = []
    for raiz in raizes:
        arvores.append(construir_arvore(raiz, 0))

    # Converter para JSON para uso no JavaScript
    import json
    arvores_json = json.dumps(arvores, ensure_ascii=False)

    # Construir lista plana para exibição simples (fallback sem JS)
    lista_convites = []
    for convite in convites_entre_contemporaneos:
        lista_convites.append({
            'convidante': convite.convidado_por,
            'convidado': convite.autor,
            'data': convite.data_criacao,
        })

    context = {
        'total_autores': total_autores,
        'total_convites_ativados': total_convites_ativados,
        'arvores': arvores,
        'arvores_json': arvores_json,
        'lista_convites': lista_convites,
        'raizes': raizes,
    }

    return render(request, 'core/rede_convites.html', context)


class OfflineView(TemplateView):
    """
    View da página offline para o PWA.
    Exibida quando o usuário está sem conexão com a internet.
    """
    template_name = 'core/offline.html'
