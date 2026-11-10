"""
Views do Vilarejo Literário
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from asgiref.sync import async_to_sync

from .models import Vilarejo, MensagemVilarejo, HistoricoCondominio
from .consumers import broadcast_mensagem, broadcast_mensagem_editada, broadcast_mensagem_excluida
from .services import (
    obter_ou_criar_vilarejo,
    obter_vizinhos_vilarejo,
    verificar_acesso_vilarejo,
    criar_mensagem,
    obter_mensagens,
    extrair_mencoes,
    obter_vilarejos_usuario,
    # Fase 3: Gestao
    convidar_morador_permanente,
    remover_morador_permanente,
    banir_usuario,
    desbanir_usuario,
    alterar_nome_vilarejo,
    obter_historico_condominio,
    obter_moradores_permanentes,
    obter_usuarios_banidos,
)
from apps.usuarios.models import User
from apps.core.utils import criar_notificacao


class MeuVilarejoView(LoginRequiredMixin, View):
    """
    View para acessar o próprio vilarejo do usuário.
    Redireciona para a view do vilarejo com o ID correto.
    """

    def get(self, request):
        vilarejo = obter_ou_criar_vilarejo(request.user)
        return redirect('vilarejo:vilarejo_detalhe', vilarejo_id=vilarejo.id)


class ListaVilarejosView(LoginRequiredMixin, View):
    """
    View para listar todos os vilarejos que o usuário tem acesso.
    Mostra vilarejos próprios, onde é morador permanente e onde é vizinho.
    """

    def get(self, request):
        vilarejos = obter_vilarejos_usuario(request.user)

        context = {
            'vilarejos': vilarejos,
            'usuario_atual': request.user,
        }

        return render(request, 'vilarejo/lista_vilarejos.html', context)


class VilarejoDetalheView(LoginRequiredMixin, View):
    """
    View principal do vilarejo.
    Exibe o chat e os vizinhos.
    """

    def get(self, request, vilarejo_id):
        # Tentar obter vilarejo - se não existir, redireciona para home
        try:
            vilarejo = Vilarejo.objects.get(id=vilarejo_id)
        except Vilarejo.DoesNotExist:
            return redirect('core:home')

        # Verificar acesso
        tem_acesso, motivo, tipo_acesso = verificar_acesso_vilarejo(request.user, vilarejo)

        if not tem_acesso:
            return redirect('core:home')

        # Obter vizinhos (recalcula ao acessar)
        vizinhos = obter_vizinhos_vilarejo(vilarejo)

        # Obter moradores permanentes
        moradores_permanentes = obter_moradores_permanentes(vilarejo)

        # Obter mensagens recentes
        mensagens = obter_mensagens(vilarejo, limite=50)

        # Verificar se é o dono
        is_dono = vilarejo.dono_id == request.user.id
        is_admin = request.user.role == 'ADMIN'

        context = {
            'vilarejo': vilarejo,
            'vizinhos': vizinhos,
            'moradores_permanentes': moradores_permanentes,
            'mensagens': mensagens,
            'is_dono': is_dono,
            'is_admin': is_admin,
            'tipo_acesso': tipo_acesso,
            'usuario_atual': request.user,
        }

        return render(request, 'vilarejo/vilarejo.html', context)


@login_required
@require_POST
def enviar_mensagem(request, vilarejo_id):
    """
    API para enviar mensagem no vilarejo.
    Retorna JSON com a mensagem criada.
    """
    vilarejo = get_object_or_404(Vilarejo, id=vilarejo_id)

    # Verificar acesso
    tem_acesso, motivo, _ = verificar_acesso_vilarejo(request.user, vilarejo)
    if not tem_acesso:
        return JsonResponse({'error': motivo}, status=403)

    conteudo = request.POST.get('conteudo', '').strip()

    try:
        mensagem = criar_mensagem(vilarejo, request.user, conteudo)

        # Extrair menções e processar notificações
        mencoes_usernames = extrair_mencoes(conteudo)
        link_vilarejo = reverse('vilarejo:vilarejo_detalhe', args=[vilarejo_id])

        # Notificar usuarios mencionados
        usuarios_notificados = set()  # Evitar duplicatas
        if mencoes_usernames:
            usuarios_mencionados = User.objects.filter(
                username__in=mencoes_usernames,
                is_active=True
            ).exclude(id=request.user.id)  # Nao notificar a si mesmo

            for usuario in usuarios_mencionados:
                try:
                    criar_notificacao(
                        usuario_destino=usuario,
                        motivo_codigo='MENCAO_VILAREJO',
                        texto=f'@{request.user.username} mencionou voce no {vilarejo.nome}',
                        link_destino=link_vilarejo,
                        usuario_origem=request.user
                    )
                    usuarios_notificados.add(usuario.id)
                except Exception:
                    pass  # Silenciosamente ignora erros de notificacao

        # Notificar o dono do vilarejo (se nao for o autor e nao foi mencionado)
        if vilarejo.dono_id != request.user.id and vilarejo.dono_id not in usuarios_notificados:
            try:
                criar_notificacao(
                    usuario_destino=vilarejo.dono,
                    motivo_codigo='MENSAGEM_VILAREJO',
                    texto=f'@{request.user.username} postou no seu vilarejo',
                    link_destino=link_vilarejo,
                    usuario_origem=request.user
                )
            except Exception:
                pass  # Silenciosamente ignora erros de notificacao

        mensagem_data = {
            'id': mensagem.id,
            'content': mensagem.conteudo,
            'author': {
                'id': mensagem.autor.id,
                'username': mensagem.autor.username,
                'nome': mensagem.autor.get_display_name(),
                'foto': mensagem.autor.foto.url if mensagem.autor.foto else None,
            },
            'created_at': mensagem.criado_em.isoformat(),
            'edited_at': None,
        }

        # Broadcast via WebSocket para todos os conectados
        # O broadcast e feito em try/except para nao bloquear a resposta HTTP
        # caso o Redis/Channels nao esteja disponivel
        try:
            async_to_sync(broadcast_mensagem)(vilarejo_id, mensagem_data)
        except Exception:
            pass  # WebSocket e opcional, nao impede o envio da mensagem

        return JsonResponse({
            'success': True,
            'mensagem': {
                'id': mensagem.id,
                'conteudo': mensagem.conteudo,
                'autor': {
                    'id': mensagem.autor.id,
                    'username': mensagem.autor.username,
                    'nome': mensagem.autor.get_display_name(),
                    'foto': mensagem.autor.foto.url if mensagem.autor.foto else None,
                },
                'criado_em': mensagem.criado_em.isoformat(),
                'editado_em': None,
            },
            'mencoes': mencoes_usernames,
        })

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def editar_mensagem(request, vilarejo_id, mensagem_id):
    """
    API para editar uma mensagem.
    Apenas o autor pode editar.
    """
    vilarejo = get_object_or_404(Vilarejo, id=vilarejo_id)
    mensagem = get_object_or_404(MensagemVilarejo, id=mensagem_id, vilarejo=vilarejo)

    # Apenas o autor pode editar
    if mensagem.autor_id != request.user.id:
        return JsonResponse({'error': 'Você não pode editar esta mensagem.'}, status=403)

    conteudo = request.POST.get('conteudo', '').strip()

    if not conteudo:
        return JsonResponse({'error': 'A mensagem não pode ser vazia.'}, status=400)

    if len(conteudo) > 500:
        return JsonResponse({'error': 'A mensagem não pode ter mais de 500 caracteres.'}, status=400)

    mensagem.conteudo = conteudo
    mensagem.editado_em = timezone.now()
    mensagem.save()

    # Broadcast edição via WebSocket
    try:
        async_to_sync(broadcast_mensagem_editada)(vilarejo_id, {
            'id': mensagem.id,
            'content': mensagem.conteudo,
            'edited_at': mensagem.editado_em.isoformat(),
        })
    except Exception:
        pass  # WebSocket e opcional

    return JsonResponse({
        'success': True,
        'mensagem': {
            'id': mensagem.id,
            'conteudo': mensagem.conteudo,
            'editado_em': mensagem.editado_em.isoformat(),
        }
    })


@login_required
@require_POST
def excluir_mensagem(request, vilarejo_id, mensagem_id):
    """
    API para excluir uma mensagem.
    Pode ser excluída pelo autor, dono do vilarejo ou admin.
    """
    vilarejo = get_object_or_404(Vilarejo, id=vilarejo_id)
    mensagem = get_object_or_404(MensagemVilarejo, id=mensagem_id, vilarejo=vilarejo)

    # Verificar permissão de exclusão
    is_autor = mensagem.autor_id == request.user.id
    is_dono = vilarejo.dono_id == request.user.id
    is_admin = request.user.role == 'ADMIN'

    if not (is_autor or is_dono or is_admin):
        return JsonResponse({'error': 'Você não pode excluir esta mensagem.'}, status=403)

    msg_id = mensagem.id
    mensagem.delete()

    # Broadcast exclusão via WebSocket
    try:
        async_to_sync(broadcast_mensagem_excluida)(vilarejo_id, msg_id)
    except Exception:
        pass  # WebSocket e opcional

    return JsonResponse({
        'success': True,
        'mensagem_id': msg_id
    })


@login_required
@require_GET
def carregar_mensagens(request, vilarejo_id):
    """
    API para carregar mais mensagens (paginação).
    """
    vilarejo = get_object_or_404(Vilarejo, id=vilarejo_id)

    # Verificar acesso
    tem_acesso, motivo, _ = verificar_acesso_vilarejo(request.user, vilarejo)
    if not tem_acesso:
        return JsonResponse({'error': motivo}, status=403)

    antes_de = request.GET.get('antes_de')
    limite = min(int(request.GET.get('limite', 50)), 100)

    mensagens = obter_mensagens(vilarejo, limite=limite, antes_de=antes_de)

    return JsonResponse({
        'mensagens': [
            {
                'id': m.id,
                'conteudo': m.conteudo,
                'autor': {
                    'id': m.autor.id,
                    'username': m.autor.username,
                    'nome': m.autor.get_display_name(),
                    'foto': m.autor.foto.url if m.autor.foto else None,
                },
                'criado_em': m.criado_em.isoformat(),
                'editado_em': m.editado_em.isoformat() if m.editado_em else None,
            }
            for m in mensagens
        ],
        'has_more': len(mensagens) == limite
    })


@login_required
@require_GET
def listar_vizinhos_para_mencao(request, vilarejo_id):
    """
    API para listar vizinhos para autocomplete de menções.
    Retorna username e nome dos vizinhos do vilarejo.
    """
    vilarejo = get_object_or_404(Vilarejo, id=vilarejo_id)

    # Verificar acesso
    tem_acesso, motivo, _ = verificar_acesso_vilarejo(request.user, vilarejo)
    if not tem_acesso:
        return JsonResponse({'error': motivo}, status=403)

    vizinhos = obter_vizinhos_vilarejo(vilarejo)

    # Incluir o dono também na lista de mencionáveis
    usuarios = [
        {
            'username': vilarejo.dono.username,
            'nome': vilarejo.dono.get_display_name(),
            'foto': vilarejo.dono.foto.url if vilarejo.dono.foto else None,
        }
    ]

    for v in vizinhos:
        usuarios.append({
            'username': v['usuario'].username,
            'nome': v['usuario'].get_display_name(),
            'foto': v['usuario'].foto.url if v['usuario'].foto else None,
        })

    return JsonResponse({'usuarios': usuarios})


# =============================================================================
# VIEWS DE GESTAO DO VILAREJO (Fase 3)
# =============================================================================

class GestaoVilarejoView(LoginRequiredMixin, View):
    """
    Pagina de gestao do vilarejo.
    Mostra moradores permanentes, banidos e historico.
    Apenas o dono pode acessar.
    """

    def get(self, request, vilarejo_id):
        # Tentar obter vilarejo - se não existir, redireciona para home
        try:
            vilarejo = Vilarejo.objects.get(id=vilarejo_id)
        except Vilarejo.DoesNotExist:
            return redirect('core:home')

        # Apenas o dono pode acessar a gestao
        if vilarejo.dono_id != request.user.id and request.user.role != 'ADMIN':
            return redirect('core:home')

        moradores = obter_moradores_permanentes(vilarejo)
        banidos = obter_usuarios_banidos(vilarejo)
        historico = obter_historico_condominio(vilarejo)
        vizinhos = obter_vizinhos_vilarejo(vilarejo)

        # IDs dos moradores permanentes (para filtrar)
        moradores_ids = {m.usuario_id for m in moradores}

        # Vizinhos que podem ser convidados (nao sao moradores permanentes)
        vizinhos_para_convidar = [v for v in vizinhos if v['usuario'].id not in moradores_ids]

        context = {
            'vilarejo': vilarejo,
            'moradores': moradores,
            'banidos': banidos,
            'historico': historico,
            'vizinhos': vizinhos,
            'vizinhos_para_convidar': vizinhos_para_convidar,
            'is_dono': vilarejo.dono_id == request.user.id,
            'is_admin': request.user.role == 'ADMIN',
        }

        return render(request, 'vilarejo/gestao.html', context)


@login_required
@require_POST
def api_convidar_morador(request, vilarejo_id):
    """API para convidar morador permanente."""
    vilarejo = get_object_or_404(Vilarejo, id=vilarejo_id)
    usuario_id = request.POST.get('usuario_id')

    if not usuario_id:
        return JsonResponse({'error': 'Usuario nao informado.'}, status=400)

    try:
        usuario = User.objects.get(id=usuario_id, is_active=True)
    except User.DoesNotExist:
        return JsonResponse({'error': 'Usuario nao encontrado.'}, status=404)

    try:
        convidar_morador_permanente(vilarejo, usuario, request.user)
        return JsonResponse({
            'success': True,
            'message': f'{usuario.get_display_name()} foi convidado como morador permanente.'
        })
    except PermissionError as e:
        return JsonResponse({'error': str(e)}, status=403)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def api_remover_morador(request, vilarejo_id):
    """API para remover morador permanente."""
    vilarejo = get_object_or_404(Vilarejo, id=vilarejo_id)
    usuario_id = request.POST.get('usuario_id')

    if not usuario_id:
        return JsonResponse({'error': 'Usuario nao informado.'}, status=400)

    try:
        usuario = User.objects.get(id=usuario_id, is_active=True)
    except User.DoesNotExist:
        return JsonResponse({'error': 'Usuario nao encontrado.'}, status=404)

    try:
        remover_morador_permanente(vilarejo, usuario, request.user)
        return JsonResponse({
            'success': True,
            'message': f'{usuario.get_display_name()} foi removido dos moradores permanentes.'
        })
    except PermissionError as e:
        return JsonResponse({'error': str(e)}, status=403)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def api_banir_usuario(request, vilarejo_id):
    """API para banir usuario."""
    vilarejo = get_object_or_404(Vilarejo, id=vilarejo_id)
    usuario_id = request.POST.get('usuario_id')
    motivo = request.POST.get('motivo', '')

    if not usuario_id:
        return JsonResponse({'error': 'Usuario nao informado.'}, status=400)

    try:
        usuario = User.objects.get(id=usuario_id, is_active=True)
    except User.DoesNotExist:
        return JsonResponse({'error': 'Usuario nao encontrado.'}, status=404)

    try:
        banir_usuario(vilarejo, usuario, request.user, motivo)
        return JsonResponse({
            'success': True,
            'message': f'{usuario.get_display_name()} foi banido do vilarejo.'
        })
    except PermissionError as e:
        return JsonResponse({'error': str(e)}, status=403)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def api_desbanir_usuario(request, vilarejo_id):
    """API para desbanir usuario."""
    vilarejo = get_object_or_404(Vilarejo, id=vilarejo_id)
    usuario_id = request.POST.get('usuario_id')

    if not usuario_id:
        return JsonResponse({'error': 'Usuario nao informado.'}, status=400)

    try:
        usuario = User.objects.get(id=usuario_id, is_active=True)
    except User.DoesNotExist:
        return JsonResponse({'error': 'Usuario nao encontrado.'}, status=404)

    try:
        desbanir_usuario(vilarejo, usuario, request.user)
        return JsonResponse({
            'success': True,
            'message': f'{usuario.get_display_name()} foi desbanido.'
        })
    except PermissionError as e:
        return JsonResponse({'error': str(e)}, status=403)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def api_alterar_nome(request, vilarejo_id):
    """API para alterar nome do vilarejo."""
    vilarejo = get_object_or_404(Vilarejo, id=vilarejo_id)
    novo_nome = request.POST.get('nome', '')

    try:
        alterar_nome_vilarejo(vilarejo, novo_nome, request.user)
        return JsonResponse({
            'success': True,
            'message': 'Nome alterado com sucesso.',
            'nome': vilarejo.nome
        })
    except PermissionError as e:
        return JsonResponse({'error': str(e)}, status=403)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_GET
def api_historico_condominio(request, vilarejo_id):
    """API para obter historico do condominio."""
    vilarejo = get_object_or_404(Vilarejo, id=vilarejo_id)

    # Verificar acesso (dono ou admin)
    if vilarejo.dono_id != request.user.id and request.user.role != 'ADMIN':
        return JsonResponse({'error': 'Sem permissao.'}, status=403)

    historico = obter_historico_condominio(vilarejo)

    return JsonResponse({
        'historico': [
            {
                'id': h.id,
                'tipo': h.tipo_evento,
                'tipo_display': h.get_tipo_evento_display(),
                'usuario_alvo': {
                    'id': h.usuario_alvo.id,
                    'username': h.usuario_alvo.username,
                    'nome': h.usuario_alvo.get_display_name(),
                } if h.usuario_alvo else None,
                'realizado_por': {
                    'id': h.realizado_por.id,
                    'username': h.realizado_por.username,
                    'nome': h.realizado_por.get_display_name(),
                } if h.realizado_por else None,
                'detalhes': h.detalhes,
                'data': h.data.isoformat(),
            }
            for h in historico
        ]
    })


@login_required
@require_POST
def api_excluir_historico(request, vilarejo_id, historico_id):
    """API para excluir um registro do historico do condominio."""
    vilarejo = get_object_or_404(Vilarejo, id=vilarejo_id)

    # Verificar permissao (dono ou admin)
    if vilarejo.dono_id != request.user.id and request.user.role != 'ADMIN':
        return JsonResponse({'error': 'Sem permissao.'}, status=403)

    try:
        registro = HistoricoCondominio.objects.get(id=historico_id, vilarejo=vilarejo)
        registro.delete()
        return JsonResponse({'success': True})
    except HistoricoCondominio.DoesNotExist:
        return JsonResponse({'error': 'Registro nao encontrado.'}, status=404)


# =============================================================================
# VIEWS DE CAPA PERSONALIZADA DO VILAREJO
# =============================================================================

@login_required
@require_POST
def api_alterar_capa(request, vilarejo_id):
    """
    API para alterar a capa personalizada do vilarejo.
    Comprime a imagem para reduzir o tamanho.
    """
    from PIL import Image
    from io import BytesIO
    from django.core.files.uploadedfile import InMemoryUploadedFile
    import sys

    vilarejo = get_object_or_404(Vilarejo, id=vilarejo_id)

    # Apenas o dono pode alterar a capa
    if vilarejo.dono_id != request.user.id:
        return JsonResponse({'error': 'Apenas o dono pode alterar a capa.'}, status=403)

    if 'capa' not in request.FILES:
        return JsonResponse({'error': 'Nenhuma imagem enviada.'}, status=400)

    arquivo = request.FILES['capa']

    # Verificar se é uma imagem valida
    if not arquivo.content_type.startswith('image/'):
        return JsonResponse({'error': 'O arquivo deve ser uma imagem.'}, status=400)

    # Limite de 10MB para upload
    if arquivo.size > 10 * 1024 * 1024:
        return JsonResponse({'error': 'A imagem deve ter no maximo 10MB.'}, status=400)

    try:
        # Abrir a imagem com Pillow
        img = Image.open(arquivo)

        # Converter para RGB se necessario (remove transparencia de PNG)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        # Redimensionar se muito grande (max 1920px de largura)
        max_width = 1920
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

        # Comprimir a imagem
        output = BytesIO()
        img.save(output, format='JPEG', quality=85, optimize=True)
        output.seek(0)

        # Criar arquivo em memoria para salvar
        compressed_file = InMemoryUploadedFile(
            output,
            'ImageField',
            f'{arquivo.name.rsplit(".", 1)[0]}.jpg',
            'image/jpeg',
            sys.getsizeof(output),
            None
        )

        # Salvar no modelo (o metodo save() cuida de deletar a antiga)
        vilarejo.capa_personalizada = compressed_file
        vilarejo.save()

        return JsonResponse({
            'success': True,
            'message': 'Capa alterada com sucesso!',
            'capa_url': vilarejo.capa_personalizada.url
        })

    except Exception as e:
        return JsonResponse({'error': f'Erro ao processar a imagem: {str(e)}'}, status=400)


@login_required
@require_POST
def api_restaurar_capa_padrao(request, vilarejo_id):
    """
    API para restaurar a capa padrao do vilarejo.
    Remove a capa personalizada.
    """
    import os

    vilarejo = get_object_or_404(Vilarejo, id=vilarejo_id)

    # Apenas o dono pode restaurar a capa
    if vilarejo.dono_id != request.user.id:
        return JsonResponse({'error': 'Apenas o dono pode restaurar a capa.'}, status=403)

    if not vilarejo.capa_personalizada:
        return JsonResponse({'error': 'O vilarejo ja esta usando a capa padrao.'}, status=400)

    try:
        # Deletar o arquivo fisico
        if os.path.isfile(vilarejo.capa_personalizada.path):
            os.remove(vilarejo.capa_personalizada.path)

        # Limpar o campo
        vilarejo.capa_personalizada = None
        vilarejo.save()

        return JsonResponse({
            'success': True,
            'message': 'Capa restaurada para o padrao!'
        })

    except Exception as e:
        return JsonResponse({'error': f'Erro ao restaurar a capa: {str(e)}'}, status=400)
