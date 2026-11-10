from django.urls import path
from .views import (
    HomeView,
    PaginaEstaticaView,
    FaleConoscoView,
    listar_notificacoes_nao_lidas,
    marcar_notificacao_como_lida,
    rede_convites_view,
    OfflineView
)

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('manifesto/', PaginaEstaticaView.as_view(), {'slug': 'manifesto'}, name='pagina_manifesto'),
    path('quem-somos/', PaginaEstaticaView.as_view(), {'slug': 'quem-somos'}, name='pagina_quem_somos'),
    path('selo-livre-de-ia/', PaginaEstaticaView.as_view(), {'slug': 'selo-livre-de-ia'}, name='pagina_selo'),
    path('termos-de-uso/', PaginaEstaticaView.as_view(), {'slug': 'termos-de-uso'}, name='pagina_termos'),
    path('transparencia-algoritmica/', PaginaEstaticaView.as_view(), {'slug': 'transparencia-algoritmica'}, name='pagina_transparencia'),
    path('fale-conosco/', FaleConoscoView.as_view(), name='fale_conosco'),
    path('rede-de-convites/', rede_convites_view, name='rede_convites'),

    # Notificações (Item 5.1 do ROADMAP)
    path('notificacoes/listar/', listar_notificacoes_nao_lidas, name='listar_notificacoes'),
    path('notificacoes/<int:notificacao_id>/marcar-lida/', marcar_notificacao_como_lida, name='marcar_notificacao_lida'),

    # PWA - Página Offline
    path('offline/', OfflineView.as_view(), name='offline'),
]
