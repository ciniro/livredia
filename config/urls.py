"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.shortcuts import redirect


def custom_404(request, exception):
    """Handler global para erros 404 - redireciona para home."""
    return redirect('core:home')
from apps.textos.views import AcervoTextos, GaleriaAutores
from apps.usuarios.views import (
    PerfilPublicoView,
    PerfilLeitorAutorView,
    ListaFavoritosView,
    ListaLidosView,
    ListaLerDepoisView,
    ListaCartoesAssinadosView,
    ListaNotificacoesView,
    ListaComentariosView,
    ListaAutoresSeguidosView,
    ListaSelosEspeciaisView,
)
from apps.painel_admin.views import email_tracking_view

urlpatterns = [
    # PWA - Service Worker (deve estar na raiz para ter escopo completo)
    path('service-worker.js', TemplateView.as_view(
        template_name='core/service-worker.js',
        content_type='application/javascript'
    ), name='service-worker'),

    path('admin/', admin.site.urls),
    path('contas/', include('apps.usuarios.urls')),
    path('contas/', include('allauth.urls')),  # URLs do django-allauth para OAuth
    path('painel-admin/', include('apps.painel_admin.urls')),  # Área administrativa (Dashboard e gestão global)
    path('autor/', include('apps.painel_autor.urls')),  # Área do autor (Dashboard, Meus Textos, Editor)
    path('acervo/', AcervoTextos.as_view(), name='acervo_textos'),  # Tela 9: Acervo de Textos
    path('autores/', GaleriaAutores.as_view(), name='galeria_autores'),  # Tela 10: Galeria de Autores
    path('texto/', include('apps.textos.urls')),  # URLs do app textos (leitura, comentários)
    path('vilarejo/', include('apps.vilarejo.urls')),  # Vilarejo Literário
    # Perfil Público (Item 5.3 do ROADMAP) - Deve vir ANTES do include do core
    path('@<str:username>/', PerfilPublicoView.as_view(), name='perfil_publico'),
    # Perfil de Leitor para Autores (exibe estatísticas de leitor)
    path('@<str:username>/leitor/', PerfilLeitorAutorView.as_view(), name='perfil_leitor_autor'),

    # SEÇÃO b) do ROADMAP 1.1: Páginas "Ver mais" das Listas de Textos
    path('@<str:username>/favoritos/', ListaFavoritosView.as_view(), name='lista_favoritos'),
    path('@<str:username>/lidos/', ListaLidosView.as_view(), name='lista_lidos'),
    path('@<str:username>/ler-mais-tarde/', ListaLerDepoisView.as_view(), name='lista_ler_depois'),
    path('@<str:username>/cartoes-assinados/', ListaCartoesAssinadosView.as_view(), name='lista_cartoes'),

    # SEÇÃO c) do ROADMAP 1.1: Página "Ver mais" de Notificações
    path('@<str:username>/notificacoes/', ListaNotificacoesView.as_view(), name='lista_notificacoes'),

    # SEÇÃO d) do ROADMAP 1.1: Página "Ver mais" de Comentários
    path('@<str:username>/comentarios/', ListaComentariosView.as_view(), name='lista_comentarios'),

    # SEÇÃO e) do ROADMAP 1.1: Páginas "Ver mais" de Autores Prediletos
    path('@<str:username>/autores-seguidos/', ListaAutoresSeguidosView.as_view(), name='lista_autores_seguidos'),
    path('@<str:username>/selos-especiais/', ListaSelosEspeciaisView.as_view(), name='lista_selos_especiais'),

    # E-mail tracking (pixel de rastreamento para comunicação geral)
    path('email/tracking/<str:token>/', email_tracking_view, name='email_tracking'),

    path('', include('apps.core.urls')),
]

# Servir arquivos de media em desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Handler global para 404 - redireciona para home
handler404 = custom_404
