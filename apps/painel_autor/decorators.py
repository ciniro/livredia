"""
Decorators customizados para área do autor.
"""
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from functools import wraps


def autor_required(view_func):
    """
    Decorator que verifica se usuário está autenticado E pode acessar o painel do autor.

    Comportamento:
    - Se não autenticado: redireciona para login
    - Se autenticado mas não pode acessar painel do autor: redireciona para home com mensagem de erro

    Usuário pode acessar painel do autor se:
    - role = AUTOR (com ou sem is_admin), OU
    - role = ADMIN (administradores puros também podem ser autores)
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Primeiro verifica autenticação
        if not request.user.is_authenticated:
            return redirect('usuarios:login')

        # Depois verifica se pode acessar painel do autor
        if not request.user.pode_acessar_painel_autor():
            messages.error(
                request,
                'Você não tem permissão para acessar a área do autor.'
            )
            return redirect('core:home')

        # Se passou nas verificações, executa a view
        return view_func(request, *args, **kwargs)

    return _wrapped_view
