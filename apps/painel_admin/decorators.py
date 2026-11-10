"""
Decorators customizados para área administrativa.
"""
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from functools import wraps


def admin_required(view_func):
    """
    Decorator que verifica se usuário está autenticado E pode acessar o painel admin.

    Comportamento:
    - Se não autenticado: redireciona para login
    - Se autenticado mas não pode acessar painel admin: redireciona para home com mensagem de erro

    Usuário pode acessar painel admin se:
    - role = ADMIN (independente de is_admin), OU
    - role = AUTOR e is_admin = True
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Primeiro verifica autenticação
        if not request.user.is_authenticated:
            return redirect('usuarios:login')

        # Depois verifica se pode acessar painel admin
        if not request.user.pode_acessar_painel_admin():
            messages.error(
                request,
                'Você não tem permissão para acessar a área administrativa.'
            )
            return redirect('core:home')

        # Se passou nas verificações, executa a view
        return view_func(request, *args, **kwargs)

    return _wrapped_view
