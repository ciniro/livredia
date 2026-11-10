"""
Middlewares personalizados do projeto LIVRE DIA
"""

from django.shortcuts import redirect
from django.urls import reverse


class Redirect404Middleware:
    """
    Middleware que intercepta todas as respostas 404 e redireciona para a home.
    Funciona tanto em DEBUG=True quanto em DEBUG=False.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Se a resposta for 404, redireciona para home
        if response.status_code == 404:
            # Não redirecionar requisições de arquivos estáticos ou media
            path = request.path
            if not (path.startswith('/static/') or
                    path.startswith('/media/') or
                    path.startswith('/admin/')):
                return redirect('core:home')

        return response
