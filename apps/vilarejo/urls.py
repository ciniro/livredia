"""
URLs do Vilarejo Literário
"""

from django.urls import path, re_path
from django.shortcuts import redirect
from . import views


def vilarejo_catch_all(request, path=''):
    """Redireciona URLs inválidas do vilarejo para a home."""
    return redirect('core:home')


app_name = 'vilarejo'

urlpatterns = [
    # Página principal (redireciona para o próprio vilarejo)
    path('', views.MeuVilarejoView.as_view(), name='meu_vilarejo'),

    # Lista de vilarejos do usuário
    path('lista/', views.ListaVilarejosView.as_view(), name='lista_vilarejos'),

    # Vilarejo específico
    path('<int:vilarejo_id>/', views.VilarejoDetalheView.as_view(), name='vilarejo_detalhe'),

    # API de mensagens
    path('<int:vilarejo_id>/mensagem/', views.enviar_mensagem, name='enviar_mensagem'),
    path('<int:vilarejo_id>/mensagem/<int:mensagem_id>/editar/', views.editar_mensagem, name='editar_mensagem'),
    path('<int:vilarejo_id>/mensagem/<int:mensagem_id>/excluir/', views.excluir_mensagem, name='excluir_mensagem'),
    path('<int:vilarejo_id>/mensagens/', views.carregar_mensagens, name='carregar_mensagens'),

    # API de menções
    path('<int:vilarejo_id>/vizinhos/', views.listar_vizinhos_para_mencao, name='listar_vizinhos'),

    # Gestão do vilarejo (Fase 3)
    path('<int:vilarejo_id>/gestao/', views.GestaoVilarejoView.as_view(), name='gestao'),
    path('<int:vilarejo_id>/gestao/convidar-morador/', views.api_convidar_morador, name='convidar_morador'),
    path('<int:vilarejo_id>/gestao/remover-morador/', views.api_remover_morador, name='remover_morador'),
    path('<int:vilarejo_id>/gestao/banir/', views.api_banir_usuario, name='banir_usuario'),
    path('<int:vilarejo_id>/gestao/desbanir/', views.api_desbanir_usuario, name='desbanir_usuario'),
    path('<int:vilarejo_id>/gestao/alterar-nome/', views.api_alterar_nome, name='alterar_nome'),
    path('<int:vilarejo_id>/gestao/historico/', views.api_historico_condominio, name='historico_condominio'),
    path('<int:vilarejo_id>/gestao/historico/<int:historico_id>/excluir/', views.api_excluir_historico, name='excluir_historico'),

    # Capa personalizada
    path('<int:vilarejo_id>/alterar-capa/', views.api_alterar_capa, name='alterar_capa'),
    path('<int:vilarejo_id>/restaurar-capa/', views.api_restaurar_capa_padrao, name='restaurar_capa'),

    # Catch-all: redireciona qualquer URL inválida para home
    re_path(r'^.+$', vilarejo_catch_all, name='catch_all'),
]
