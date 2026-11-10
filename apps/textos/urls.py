from django.urls import path
from .views import (
    TextoDetailView,
    deletar_comentario,
    atualizar_tempo_leitura,
    buscar_usuarios_mencao,
    salvar_configuracao_leitura,
    download_pdf_texto,
    download_bibtex_texto,
    download_abnt_texto,
    assinar_cartao,
    listar_assinaturas,
    toggle_favorito,
    toggle_lido,
    toggle_leitura_posterior,
    sorteia_texto,
    sorteia_texto_forcado,
    toggle_seguir_autor
)

app_name = 'textos'

urlpatterns = [
    # API: Atualizar tempo de leitura (JavaScript heartbeat)
    path('api/tracking/tempo-leitura/', atualizar_tempo_leitura, name='atualizar_tempo_leitura'),

    # API: Buscar usuários para menção (Item 2 do ROADMAP)
    path('api/usuarios/buscar/', buscar_usuarios_mencao, name='buscar_usuarios_mencao'),

    # API: Salvar configurações de leitura (Item 3.2 do ROADMAP)
    path('api/salvar-config-leitura/', salvar_configuracao_leitura, name='salvar_config_leitura'),

    # Deletar comentário (HTMX)
    path('comentario/<int:comentario_id>/deletar/', deletar_comentario, name='deletar_comentario'),

    # Downloads de texto (Item 3.5 do ROADMAP)
    path('<int:pk>/download/pdf/', download_pdf_texto, name='download_pdf'),
    path('<int:pk>/download/bibtex/', download_bibtex_texto, name='download_bibtex'),
    path('<int:pk>/download/abnt/', download_abnt_texto, name='download_abnt'),

    # Cartão da Biblioteca (Item 3.6 do ROADMAP)
    path('<int:pk>/assinar-cartao/', assinar_cartao, name='assinar_cartao'),
    path('<int:pk>/cartao/assinaturas/', listar_assinaturas, name='listar_assinaturas'),

    # Botões de Ação Rápida (Item 2.2 do ROADMAP)
    path('<int:pk>/toggle-favorito/', toggle_favorito, name='toggle_favorito'),
    path('<int:pk>/toggle-lido/', toggle_lido, name='toggle_lido'),
    path('sortear/<int:texto_atual_id>/<str:tipo_sorteio>/', sorteia_texto, name='sorteia_texto'),
    path('sortear-forcado/<int:texto_atual_id>/', sorteia_texto_forcado, name='sorteia_texto_forcado'),

    # Lista de Leitura - Ler Mais Tarde (Item 4 do ROADMAP)
    path('<int:pk>/toggle-leitura-posterior/', toggle_leitura_posterior, name='toggle_leitura_posterior'),

    # Autores Seguidos (Item 3 do ROADMAP)
    path('autor/<int:autor_id>/toggle-seguir/', toggle_seguir_autor, name='toggle_seguir_autor'),

    # Tela 8: Leitura de Texto (por ID)
    path('<int:pk>/', TextoDetailView.as_view(), name='leitura_texto'),
]
