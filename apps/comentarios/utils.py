"""
Utilitários do app comentarios.

Funções auxiliares para processamento de menções em comentários.
"""
import re
from django.contrib.auth import get_user_model

User = get_user_model()


def extrair_mencoes(texto):
    """
    Extrai menções @username de um texto.

    Busca padrões @username no texto e valida se os usuários existem
    e não estão suspensos.

    Args:
        texto (str): Texto contendo possíveis menções

    Returns:
        list[User]: Lista de objetos User mencionados (validados)

    Example:
        >>> texto = "Ótimo texto @joao e @maria! Concordo com @pedro"
        >>> usuarios = extrair_mencoes(texto)
        >>> [u.username for u in usuarios]
        ['joao', 'maria', 'pedro']

    Note:
        - Username deve conter apenas letras, números e underscores
        - Busca é case-insensitive
        - Usuários suspensos são ignorados
        - Usernames duplicados retornam apenas uma vez
    """
    # Regex: @ seguido de letras, números, underscores e hífens (1 ou mais caracteres)
    padrao = r'@([\w-]+)'
    usernames_encontrados = re.findall(padrao, texto)

    # Remover duplicatas mantendo ordem
    usernames_unicos = []
    for username in usernames_encontrados:
        if username.lower() not in [u.lower() for u in usernames_unicos]:
            usernames_unicos.append(username)

    # Validar que usernames existem e não estão suspensos
    usuarios_validos = []
    for username in usernames_unicos:
        try:
            user = User.objects.get(username__iexact=username, is_suspended=False)
            usuarios_validos.append(user)
        except User.DoesNotExist:
            # Username não existe ou usuário está suspenso, ignorar
            pass

    return usuarios_validos


def processar_mencoes_comentario(comentario):
    """
    Processa menções em um comentário e cria notificações.

    Extrai todas as menções do comentário e cria uma notificação
    separada para cada usuário mencionado (exceto o próprio autor).

    Args:
        comentario (Comentario): Objeto Comentario contendo menções

    Returns:
        int: Número de notificações criadas

    Example:
        >>> from apps.comentarios.models import Comentario
        >>> comentario = Comentario.objects.get(pk=123)
        >>> num_notificacoes = processar_mencoes_comentario(comentario)
        >>> print(f"{num_notificacoes} notificações criadas")

    Note:
        - Não notifica o próprio autor do comentário
        - Cria uma notificação separada por usuário mencionado
        - Link aponta para a tela de leitura do texto
        - Usa motivo 'MENCAO_COMENTARIO'
    """
    from apps.core.utils import criar_notificacao

    # Extrair usuários mencionados
    usuarios_mencionados = extrair_mencoes(comentario.conteudo)

    notificacoes_criadas = 0

    # Criar notificações para cada menção
    for usuario_destino in usuarios_mencionados:
        # Não notificar o próprio autor do comentário
        if usuario_destino.id == comentario.autor.id:
            continue

        # Montar texto da notificação
        autor_username = comentario.autor.username
        texto = f"@{autor_username} marcou você em um comentário."

        # Link de destino (vai para o texto onde o comentário foi feito)
        link = f"/texto/{comentario.texto.pk}/"

        # Criar notificação
        try:
            criar_notificacao(
                usuario_destino=usuario_destino,
                motivo_codigo='MENCAO_COMENTARIO',
                texto=texto,
                link_destino=link,
                usuario_origem=comentario.autor
            )
            notificacoes_criadas += 1
        except Exception as e:
            # Log do erro mas não quebra o fluxo
            print(f"Erro ao criar notificação para {usuario_destino.username}: {e}")
            continue

    return notificacoes_criadas
