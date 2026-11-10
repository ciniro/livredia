"""
URLs do painel administrativo.
"""
from django.urls import path
from . import views

app_name = 'painel_admin'

urlpatterns = [
    # Dashboard Principal (Tela 17)
    path('dashboard/', views.AdminDashboardView.as_view(), name='dashboard'),

    # ========================================
    # GESTÃO DE AUTORES
    # ========================================

    # Tela 17 - Gestão de Autores (Listagem)
    path('gestao/autores/', views.GestaoAutoresListView.as_view(), name='gestao_autores'),

    # Tela 18 - Formulário de Novo Autor
    path('gestao/autores/novo/', views.AdminAutorCreateView.as_view(), name='novo_autor'),

    # Formulário de Edição de Autor
    path('gestao/autores/<int:pk>/editar/', views.AdminAutorEditView.as_view(), name='editar_autor'),

    # Configuração de Convites de Autores
    path('gestao/autores/convites/', views.configuracao_convites_view, name='configuracao_convites'),

    # Gestão de Autores Clássicos
    path('gestao/autores/classicos/', views.gestao_autores_classicos_view, name='gestao_autores_classicos'),

    # Ações - Gestão de Autores
    path('gestao/autores/<int:pk>/toggle-suspender/', views.toggle_suspender_autor, name='toggle_suspender_autor'),
    path('gestao/autores/<int:pk>/toggle-admin/', views.toggle_admin_autor, name='toggle_admin_autor'),
    path('gestao/autores/<int:pk>/excluir/', views.excluir_autor, name='excluir_autor'),
    path('gestao/autores/<int:pk>/gerar-link/', views.gerar_link_boas_vindas, name='gerar_link_boas_vindas'),
    path('gestao/autores/<int:pk>/enviar-convite/', views.enviar_convite_email, name='enviar_convite_email'),

    # Tela 19 - Página de Boas-Vindas ao Autor (Link de Ativação)
    path('convite/<str:token>/', views.convite_autor_view, name='convite_autor'),

    # Página de Agradecimento após Ativação
    path('bem-vindo-autor/', views.autor_boas_vindas, name='autor_boas_vindas'),

    # ========================================
    # GESTÃO DE LEITORES
    # ========================================

    # Tela 20 - Gestão de Leitores (Listagem)
    path('gestao/leitores/', views.GestaoLeitoresListView.as_view(), name='gestao_leitores'),

    # Formulário de Edição de Leitor
    path('gestao/leitores/<int:pk>/editar/', views.EditarLeitorView.as_view(), name='editar_leitor'),

    # Ações - Gestão de Leitores
    path('gestao/leitores/<int:pk>/toggle-suspender/', views.toggle_suspender_leitor, name='toggle_suspender_leitor'),
    path('gestao/leitores/<int:pk>/excluir/', views.excluir_leitor, name='excluir_leitor'),

    # ========================================
    # GESTÃO DE ADMINISTRADORES
    # ========================================

    # Gestão de Administradores (Listagem)
    path('gestao/administradores/', views.GestaoAdministradoresListView.as_view(), name='gestao_administradores'),

    # Formulário de Novo Administrador Puro (apenas ADMIN puro)
    path('gestao/administradores/novo/', views.NovoAdminView.as_view(), name='novo_admin'),

    # Formulário de Edição de Administrador (apenas ADMIN puro)
    path('gestao/administradores/<int:pk>/editar/', views.EditarAdminView.as_view(), name='editar_admin'),

    # Ações - Gestão de Administradores
    path('gestao/administradores/<int:pk>/remover-admin/', views.remover_admin_autor, name='remover_admin_autor'),
    path('gestao/administradores/<int:pk>/excluir/', views.excluir_admin, name='excluir_admin'),

    # ========================================
    # MODERAÇÃO GLOBAL
    # ========================================

    # Tela 19 - Moderação Global (Listagem de Comentários)
    path('moderacao/', views.ModeracaoGlobalListView.as_view(), name='moderacao_global'),

    # Ações - Moderação de Comentários
    path('moderacao/<int:pk>/aprovar/', views.aprovar_comentario, name='aprovar_comentario'),
    path('moderacao/<int:pk>/rejeitar/', views.rejeitar_comentario, name='rejeitar_comentario'),
    path('moderacao/<int:pk>/excluir/', views.excluir_comentario_admin, name='excluir_comentario_admin'),

    # ========================================
    # GESTÃO DE PÁGINAS
    # ========================================

    # Tela 21 - Gestão de Páginas: Edição de Página Estática
    path('cms/editar/<slug:slug>/', views.EditarPaginaView.as_view(), name='editar_pagina'),

    # ========================================
    # GESTÃO DE OBRAS
    # ========================================

    # Gestão de Obras (Listagem)
    path('gestao/obras/', views.GestaoObrasListView.as_view(), name='gestao_obras'),

    # Ações - Gestão de Obras
    path('gestao/obras/<int:pk>/toggle-suspender/', views.toggle_suspender_texto, name='toggle_suspender_texto'),
    path('gestao/obras/<int:pk>/excluir/', views.excluir_texto, name='excluir_texto'),

    # ========================================
    # GESTÃO DE TEMAS (TAGS)
    # ========================================

    # Gestão de Temas (Listagem)
    path('gestao/temas/', views.GestaoTemasListView.as_view(), name='gestao_temas'),

    # Formulário de Novo Tema
    path('gestao/temas/novo/', views.NovoTemaView.as_view(), name='novo_tema'),

    # Formulário de Edição de Tema
    path('gestao/temas/<int:pk>/editar/', views.EditarTemaView.as_view(), name='editar_tema'),

    # Ações - Gestão de Temas
    path('gestao/temas/<int:pk>/excluir/', views.excluir_tema, name='excluir_tema'),

    # ========================================
    # CONTATOS ADMINISTRATIVOS
    # ========================================

    # Gestão de Contatos Administrativos (Listagem)
    path('contatos/', views.ContatosAdministrativosView.as_view(), name='contatos_administrativos'),

    # Formulário de Novo Contato
    path('contatos/novo/', views.NovoContatoAdministrativoView.as_view(), name='novo_contato'),

    # Formulário de Edição de Contato
    path('contatos/<int:pk>/editar/', views.EditarContatoAdministrativoView.as_view(), name='editar_contato'),

    # Ações - Gestão de Contatos
    path('contatos/<int:pk>/excluir/', views.excluir_contato_administrativo, name='excluir_contato'),

    # ========================================
    # TEMAS DE LEITURA
    # ========================================

    # Gestão de Temas de Leitura (Listagem)
    path('temas-leitura/', views.TemasLeituraListView.as_view(), name='temas_leitura'),

    # Formulário de Novo Tema de Leitura
    path('temas-leitura/novo/', views.NovoTemaLeituraView.as_view(), name='novo_tema_leitura'),

    # Formulário de Edição de Tema de Leitura
    path('temas-leitura/<int:pk>/editar/', views.EditarTemaLeituraView.as_view(), name='editar_tema_leitura'),

    # Ações - Gestão de Temas de Leitura
    path('temas-leitura/<int:pk>/excluir/', views.excluir_tema_leitura, name='excluir_tema_leitura'),

    # ========================================
    # COMUNICAÇÃO GERAL (E-MAIL MARKETING)
    # ========================================

    # Lista de comunicações enviadas
    path('comunicacao-geral/', views.comunicacao_geral_lista_view, name='comunicacao_geral_lista'),

    # Nova comunicação (formulário)
    path('comunicacao-geral/nova/', views.comunicacao_geral_nova_view, name='comunicacao_geral_nova'),

    # Preview do e-mail
    path('comunicacao-geral/preview/', views.comunicacao_geral_preview_view, name='comunicacao_geral_preview'),

    # API: Contar destinatários (AJAX)
    path('comunicacao-geral/contar/', views.comunicacao_geral_contar_view, name='comunicacao_geral_contar'),

    # API: Enviar teste para admin logado (AJAX)
    path('comunicacao-geral/enviar-teste/', views.comunicacao_geral_enviar_teste_view, name='comunicacao_geral_enviar_teste'),

    # API: Enviar para todos (AJAX)
    path('comunicacao-geral/enviar/', views.comunicacao_geral_enviar_view, name='comunicacao_geral_enviar'),

    # Detalhes de uma comunicação enviada
    path('comunicacao-geral/<int:pk>/', views.comunicacao_geral_detalhes_view, name='comunicacao_geral_detalhes'),

    # Excluir comunicação
    path('comunicacao-geral/<int:pk>/excluir/', views.comunicacao_geral_excluir_view, name='comunicacao_geral_excluir'),

]
