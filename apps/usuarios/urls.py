from django.urls import path
from .views import (
    CustomLoginView,
    CustomLogoutView,
    CadastroLeitorView,
    MinhaContaView,
    ExcluirContaView,
    ConfirmarEmailView,
    ConfirmacaoEnviadaView,
    ReenviarConfirmacaoView,
    SolicitarRecuperacaoView,
    RedefinirSenhaView,
    verificar_username_disponivel,
    PerfilPublicoView,
    ConfiguracoesView,
    alterar_tema_plataforma,
    selo_detalhes_json,
    marcar_selo_exibido,
    limpar_selos_sessao,
    toggle_visibilidade_perfil,
    excluir_notificacao,
    excluir_comentario,
    remover_selo_especial,
    desativar_avisos_maioridade,
    backup_textos_autor,
    # Views para Login com Google
    ComplementoCadastroGoogleView,
    vincular_google,
    desvincular_google,
    # Gerenciamento de preferências de e-mail
    email_preferences_view,
)

app_name = 'usuarios'

urlpatterns = [
    # Autenticação
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('cadastro/', CadastroLeitorView.as_view(), name='cadastro_leitor'),

    # Confirmação de E-mail
    path('confirmar-email/<uuid:token>/', ConfirmarEmailView.as_view(), name='confirmar_email'),
    path('confirmacao-enviada/', ConfirmacaoEnviadaView.as_view(), name='confirmacao_enviada'),
    path('reenviar-confirmacao/', ReenviarConfirmacaoView.as_view(), name='reenviar_confirmacao'),

    # Recuperação de Senha (Item 14 do ROADMAP)
    path('esqueci-senha/', SolicitarRecuperacaoView.as_view(), name='solicitar_recuperacao'),
    path('redefinir-senha/<uuid:token>/', RedefinirSenhaView.as_view(), name='redefinir_senha'),

    # Gerenciamento de Conta
    path('minha-conta/', MinhaContaView.as_view(), name='minha_conta'),
    path('excluir-conta/', ExcluirContaView.as_view(), name='excluir_conta'),

    # Configurações (Item 4 do ROADMAP)
    path('configuracoes/', ConfiguracoesView.as_view(), name='configuracoes'),

    # AJAX: Alterar tema da plataforma (light/dark) sem reload
    path('api/alterar-tema/', alterar_tema_plataforma, name='alterar_tema_plataforma'),

    # AJAX Endpoints (Item 5.1 do ROADMAP)
    path('api/verificar-username/', verificar_username_disponivel, name='verificar_username'),

    # ETAPA 7 - Sistema de Selos: Endpoints para Modal de Celebração
    path('selo-detalhes/<int:selo_id>/', selo_detalhes_json, name='selo_detalhes'),
    path('marcar-selo-exibido/<int:selo_id>/', marcar_selo_exibido, name='marcar_selo_exibido'),
    path('limpar-selos-sessao/', limpar_selos_sessao, name='limpar_selos_sessao'),

    # Item 1.1 do ROADMAP - Perfil de Não-Autores: Toggle de Visibilidade
    path('api/toggle-visibilidade-perfil/', toggle_visibilidade_perfil, name='toggle_visibilidade_perfil'),

    # SEÇÃO c) do ROADMAP 1.1: Excluir Notificação
    path('api/notificacao/<int:notificacao_id>/excluir/', excluir_notificacao, name='excluir_notificacao'),

    # SEÇÃO d) do ROADMAP 1.1: Excluir Comentário
    path('api/comentario/<int:comentario_id>/excluir/', excluir_comentario, name='excluir_comentario'),

    # SEÇÃO e) do ROADMAP 1.1: Remover Selo Leitor Especial
    path('api/autor/<int:autor_id>/remover-selo-especial/', remover_selo_especial, name='remover_selo_especial'),

    # MELHORIA 73: Desativar Avisos de Conteúdo Sensível
    path('api/desativar-avisos-maioridade/', desativar_avisos_maioridade, name='desativar_avisos_maioridade'),

    # Login com Google (django-allauth)
    path('google/complemento-cadastro/', ComplementoCadastroGoogleView.as_view(), name='complemento_cadastro_google'),
    path('google/vincular/', vincular_google, name='vincular_google'),
    path('google/desvincular/', desvincular_google, name='desvincular_google'),

    # Backup de Textos para Autores (ROADMAP Item 1)
    path('backup-textos/', backup_textos_autor, name='backup_textos'),

    # Gerenciamento de preferências de e-mail via link do e-mail
    path('email-prefs/<str:token>/', email_preferences_view, name='email_preferences'),
]
