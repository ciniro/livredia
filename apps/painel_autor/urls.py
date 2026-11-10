"""
URLs do painel do autor.

Todas as rotas deste app estão sob o prefixo /autor/ (configurado no config/urls.py).
"""
from django.urls import path
from . import views

app_name = 'painel_autor'

urlpatterns = [
    # ========================================
    # DASHBOARD
    # ========================================

    # Dashboard do Autor
    path('', views.DashboardAutorView.as_view(), name='dashboard'),

    # ========================================
    # PERSONALIZAÇÃO
    # ========================================

    # Personalização da Área do Autor (Tema)
    path('personalizar/', views.ConfiguracoesAutorView.as_view(), name='configuracoes'),

    # Cores Light Mode
    path('personalizar/aplicar-cor/<str:cor>/', views.aplicar_cor, name='aplicar_cor'),
    path('personalizar/remover-cor/', views.remover_cor, name='remover_cor'),

    # Cores Dark Mode
    path('personalizar/aplicar-cor-dark/<str:cor>/', views.aplicar_cor_dark, name='aplicar_cor_dark'),
    path('personalizar/remover-cor-dark/', views.remover_cor_dark, name='remover_cor_dark'),

    # Ícones
    path('personalizar/aplicar-emoji/<str:emoji>/', views.aplicar_emoji, name='aplicar_emoji'),
    path('personalizar/remover-emoji/', views.remover_emoji, name='remover_emoji'),

    # ========================================
    # MODERAÇÃO DE COMENTÁRIOS
    # ========================================

    # Moderação de Comentários do Autor
    path('moderacao/', views.ModeracaoAutorListView.as_view(), name='moderacao_autor'),
    path('moderacao/aprovar/<int:pk>/', views.aprovar_comentario_autor, name='aprovar_comentario_autor'),
    path('moderacao/rejeitar/<int:pk>/', views.rejeitar_comentario_autor, name='rejeitar_comentario_autor'),
    path('moderacao/excluir/<int:pk>/', views.excluir_comentario_autor, name='excluir_comentario_autor'),

    # ========================================
    # GESTÃO DE TEXTOS (Telas 20 e 21)
    # ========================================

    # Tela 21: Meus Textos (Listagem)
    path('textos/', views.MeusTextosListView.as_view(), name='meus_textos'),
    path('textos/<int:pk>/excluir/', views.excluir_texto, name='excluir_texto'),
    path('textos/<int:pk>/toggle-status/', views.toggle_status_texto, name='toggle_status_texto'),

    # Tela 20: Editor de Texto (Criar/Editar)
    path('textos/novo/', views.NovoTextoView.as_view(), name='novo_texto'),
    path('textos/<int:pk>/editar/', views.EditarTextoView.as_view(), name='editar_texto'),

    # Guia do Editor (Ajuda)
    path('textos/guia-editor/', views.GuiaEditorView.as_view(), name='guia_editor'),

    # AJAX: Auto-save de rascunho
    path('textos/auto-save/', views.auto_save_texto, name='auto_save_texto'),

    # AJAX: Gerenciar tags
    path('tags/criar/', views.criar_tag_ajax, name='criar_tag_ajax'),
    path('tags/editar/', views.editar_tag_ajax, name='editar_tag_ajax'),
    path('tags/excluir/', views.excluir_tag_ajax, name='excluir_tag_ajax'),

    # ========================================
    # SISTEMA DE SELOS - MEUS SEGUIDORES (Item 1 do ROADMAP - ETAPA 2)
    # ========================================

    # Tela de Seguidores (Versão Básica)
    path('seguidores/', views.MeusSeguidoresView.as_view(), name='meus_seguidores'),

    # ETAPA 5: Marcar/Desmarcar Leitor Especial
    path('seguidores/<int:seguidor_id>/marcar-especial/', views.marcar_leitor_especial, name='marcar_leitor_especial'),
    path('seguidores/<int:seguidor_id>/desmarcar-especial/', views.desmarcar_leitor_especial, name='desmarcar_leitor_especial'),

    # ETAPA 6: Remover Seguidor
    path('seguidores/<int:seguidor_id>/remover/', views.remover_seguidor, name='remover_seguidor'),

    # Ver Comentários do Seguidor
    path('seguidores/<int:seguidor_id>/comentarios/', views.ver_comentarios_seguidor, name='ver_comentarios_seguidor'),

    # ========================================
    # MONETIZAÇÃO VIA PIX (Item 1 do ROADMAP)
    # ========================================

    # Cadastro/Edição/Remoção de Chave PIX
    path('monetizacao/', views.monetizacao_view, name='monetizacao'),

    # ========================================
    # CONVIDAR NOVO AUTOR
    # ========================================

    # Formulário para convidar novo autor
    path('convidar-autor/', views.convidar_autor_view, name='convidar_autor'),
]
