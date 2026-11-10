"""
Template filters e tags customizadas para comentários.

Filtros:
- renderizar_mencoes: Converte @username em links clicáveis para perfis
"""
import re
from django import template
from django.utils.safestring import mark_safe
from django.contrib.auth import get_user_model

register = template.Library()
User = get_user_model()


@register.filter
def renderizar_mencoes(conteudo):
    """
    Converte @username em links HTML para perfil.

    Funcionalidades:
    - Valida se usuário existe
    - Verifica se usuário não está suspenso
    - Renderiza como link clicável: <a href="/@username">@username</a>
    - Se usuário não existe/suspenso: renderiza como texto simples

    Args:
        conteudo (str): Texto do comentário contendo menções

    Returns:
        SafeString: HTML com menções convertidas em links

    Usage:
        {% load comentario_extras %}
        {{ comentario.conteudo|renderizar_mencoes|safe }}

    Example:
        Input: "Ótimo texto @joao!"
        Output: 'Ótimo texto <a href="/@joao">@joao</a>!'

    Note:
        - Usuários suspensos: menção renderiza como texto simples
        - Usernames inexistentes: menção renderiza como texto simples
        - Links têm classe CSS 'text-primary hover:underline font-semibold'
        - Busca é case-insensitive mas preserva case original
    """
    def substituir_mencao(match):
        """
        Função auxiliar para substituir cada menção encontrada.

        Args:
            match: Objeto Match do regex

        Returns:
            str: HTML do link ou texto simples
        """
        username_original = match.group(1)  # Preserva case original

        try:
            # Buscar usuário (case-insensitive)
            user = User.objects.get(username__iexact=username_original)

            # Se usuário suspenso, não criar link
            if user.is_suspended:
                return f'@{username_original}'

            # Criar link para perfil (usa username do banco para garantir case correto)
            return f'<a href="/@{user.username}" class="text-primary hover:underline font-semibold">@{user.username}</a>'

        except User.DoesNotExist:
            # Username não existe, retornar como texto
            return f'@{username_original}'

    # Regex: @ seguido de letras, números, underscores e hífens
    padrao = r'@([\w-]+)'
    resultado = re.sub(padrao, substituir_mencao, conteudo)

    return mark_safe(resultado)
