from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import DetailView, ListView
from django.contrib import messages
from django.http import Http404, HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Prefetch, Sum
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta, datetime
import json
import re
import random
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .models import Texto, Visualizacao, Tag, CartaoBiblioteca, TextoFavorito, TextoLido, TextoLeituraPosterior
from apps.comentarios.models import Comentario
from apps.comentarios.forms import ComentarioForm
from apps.usuarios.models import User, AutorSeguido
from apps.core.utils import criar_notificacao


def get_client_ip(request):
    """
    Extrai o IP do cliente da requisição.
    Considera proxies e load balancers (X-Forwarded-For).
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def formatar_tempo_leitura(segundos):
    """
    Formata tempo de leitura em formato humano.

    Formato:
    - None ou 0: "0s"
    - Menos de 1 minuto: "45s"
    - Menos de 1 hora: "23min"
    - 1 hora ou mais: "14h 55min"
    """
    if not segundos or segundos <= 0:
        return "0s"

    segundos = int(segundos)
    horas = segundos // 3600
    minutos = (segundos % 3600) // 60
    segundos_restantes = segundos % 60

    if horas > 0:
        return f"{horas}h {minutos}min"
    elif minutos > 0:
        return f"{minutos}min"
    else:
        return f"{segundos_restantes}s"


class TextoDetailView(DetailView):
    """
    View para exibição completa de um texto (Tela 8 - Leitura de Texto).

    Funcionalidades:
    - Exibe texto publicado com título, subtítulo, conteúdo
    - Mostra informações do autor (avatar, nome/pseudônimo, bio)
    - Exibe Selo Livre de IA (se aplicável)
    - Lista comentários aprovados com respostas aninhadas
    - Formulário de comentários (HTMX) com moderação automática
    - Registro de visualização para analytics
    - Controles de leitura (tema + fonte) via Alpine.js

    Baseada no protótipo: prototipos_telas/leitura_de_texto_(article_view)/code.html

    IMPORTANTE: URL usa ID em vez de slug para simplicidade e estabilidade
    """
    model = Texto
    template_name = 'textos/leitura_texto.html'
    context_object_name = 'texto'
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        """
        Retorna textos publicados ou rascunhos (se o usuário for o autor).

        IMPORTANTE:
        - Textos PUBLICADOS: visíveis para todos (exceto suspensos)
        - Textos RASCUNHO: visíveis APENAS para o autor (pré-visualização)
        """
        queryset = Texto.objects.filter(
            is_suspended=False,  # Ocultar textos suspensos
            autor__is_suspended=False  # Ocultar textos de autores suspensos
        ).select_related('autor')

        # Se usuário autenticado, incluir seus próprios rascunhos
        if self.request.user.is_authenticated:
            queryset = queryset.filter(
                Q(status=Texto.Status.PUBLICADO) |  # Todos veem publicados
                Q(status=Texto.Status.RASCUNHO, autor=self.request.user)  # Autor vê seus rascunhos
            )
        else:
            # Visitantes só veem publicados
            queryset = queryset.filter(status=Texto.Status.PUBLICADO)

        return queryset

    def dispatch(self, request, *args, **kwargs):
        """
        Intercepta requisições para tratar textos não encontrados.
        Redireciona para a Home ao invés de mostrar página 404.
        """
        try:
            return super().dispatch(request, *args, **kwargs)
        except Http404:
            # Redirecionar para a Home ao invés de mostrar página 404
            messages.warning(request, 'O texto que você tentou acessar não está disponível.')
            return redirect('core:home')

    def get_object(self, queryset=None):
        """
        Busca o texto pelo ID (pk).

        Regras:
        - Textos PUBLICADOS: todos podem acessar
        - Textos RASCUNHO: apenas o autor pode acessar (pré-visualização)
        - Caso contrário: 404 (que será interceptado pelo dispatch e redirecionado para Home)
        """
        obj = super().get_object(queryset)

        # Se rascunho, verificar se é o autor
        if obj.status == Texto.Status.RASCUNHO:
            if not self.request.user.is_authenticated or obj.autor != self.request.user:
                raise Http404("Texto não encontrado ou não disponível.")

        return obj

    def get_context_data(self, **kwargs):
        """
        Adiciona comentários, formulário e visualizacao_id ao contexto.
        """
        context = super().get_context_data(**kwargs)
        texto = self.object

        # Flag para indicar modo de pré-visualização (rascunho)
        context['is_preview'] = texto.status == Texto.Status.RASCUNHO

        # Criar Prefetch para respostas (filtrando autores suspensos)
        # Respostas aprovadas de autores não suspensos
        respostas_prefetch = Prefetch(
            'respostas',
            queryset=Comentario.objects.filter(
                status=Comentario.Status.APROVADO,
                autor__is_suspended=False  # Ocultar respostas de suspensos
            ).select_related('autor').order_by('data_publicacao')
        )

        # 1. Buscar comentários (aprovados para todos + pendentes do usuário logado)
        # Apenas raiz (não respostas), ordenados do mais recente para o mais antigo
        # IMPORTANTE: Filtrar autores suspensos em todos os casos
        if self.request.user.is_authenticated:
            # Usuário logado: mostrar aprovados + seus comentários pendentes
            # (mas sempre ocultando comentários de usuários suspensos)
            comentarios_raiz = Comentario.objects.filter(
                texto=texto,
                pai=None,  # Apenas comentários principais
                autor__is_suspended=False  # Ocultar comentários de suspensos
            ).filter(
                Q(status=Comentario.Status.APROVADO) |  # Aprovados (todos veem)
                Q(status=Comentario.Status.PENDENTE, autor=self.request.user)  # Pendentes (só o autor)
            ).select_related('autor').prefetch_related(respostas_prefetch).order_by('-data_publicacao')
        else:
            # Usuário não logado: mostrar apenas aprovados de não suspensos
            comentarios_raiz = Comentario.objects.filter(
                texto=texto,
                status=Comentario.Status.APROVADO,
                pai=None,
                autor__is_suspended=False  # Ocultar comentários de suspensos
            ).select_related('autor').prefetch_related(respostas_prefetch).order_by('-data_publicacao')

        context['comentarios'] = comentarios_raiz

        # 2. Formulário de comentário (se permite comentários)
        if texto.permite_comentarios:
            context['comentario_form'] = ComentarioForm()

        # 3. Verificar se o texto permite comentários anônimos
        context['permite_anonimos'] = texto.permite_comentarios_anonimos

        # 4. Passar ID da visualização para o template (para tracking de tempo)
        if hasattr(self, 'visualizacao_atual') and self.visualizacao_atual:
            context['visualizacao_id'] = self.visualizacao_atual.id
        else:
            context['visualizacao_id'] = None

        # 5. Carregar configurações de leitura do usuário (Item 3.2 do ROADMAP)
        # Se usuário está logado, carregar configurações salvas no banco
        # Se não está logado, usar valores padrão
        if self.request.user.is_authenticated:
            try:
                config = self.request.user.configuracao
                context['tema_inicial'] = config.tema_leitura_padrao.slug  # Agora é FK, retornar slug
                context['zoom_inicial'] = config.nivel_zoom_padrao
            except:
                # Fallback se configuração não existir (não deveria acontecer por causa do signal)
                context['tema_inicial'] = 'padrao'
                context['zoom_inicial'] = 5
        else:
            # Usuário não logado: valores padrão
            context['tema_inicial'] = 'padrao'
            context['zoom_inicial'] = 5

        # 6. Carregar todos os temas ativos para carregamento dinâmico de CSS (sistema modular)
        from apps.core.models import TemaLeitura
        context['temas'] = TemaLeitura.objects.filter(ativo=True)

        # 7. Estado inicial do botão "Salvar nos melhores" (Item 2.2.1 do ROADMAP)
        # Verifica se o usuário logado já favoritou este texto
        if self.request.user.is_authenticated:
            context['texto_favoritado'] = TextoFavorito.objects.filter(
                usuario=self.request.user,
                texto=self.object
            ).exists()
        else:
            context['texto_favoritado'] = False

        # 8. Estado inicial do botão "Marcar como lido" (Item 2.2.2 do ROADMAP)
        # Verifica se o usuário logado já marcou este texto como lido
        if self.request.user.is_authenticated:
            context['texto_lido'] = TextoLido.objects.filter(
                usuario=self.request.user,
                texto=self.object
            ).exists()
        else:
            context['texto_lido'] = False

        # 9. Estado inicial do botão "Ler mais tarde" (Item 4 do ROADMAP)
        # Verifica se o usuário logado já salvou este texto para ler mais tarde
        if self.request.user.is_authenticated:
            context['na_lista_leitura'] = TextoLeituraPosterior.objects.filter(
                usuario=self.request.user,
                texto=self.object
            ).exists()
        else:
            context['na_lista_leitura'] = False

        # 10. Estado inicial do botão "Seguir"/"Deixar de seguir" (Item 3 do ROADMAP)
        # Verifica se o usuário logado está seguindo o autor deste texto
        if self.request.user.is_authenticated:
            context['seguindo_autor'] = AutorSeguido.objects.filter(
                seguidor=self.request.user,
                autor=self.object.autor
            ).exists()
        else:
            context['seguindo_autor'] = False

        # 11. ETAPA 8 - Sistema de Selos: Buscar leitores especiais do autor
        # Cria um set (para lookup O(1)) com os IDs dos seguidores que são leitores especiais
        # Usado no template _comentario.html para exibir selo ao lado do nome
        leitores_especiais = AutorSeguido.objects.filter(
            autor=texto.autor,
            is_leitor_especial=True
        ).values_list('seguidor_id', flat=True)
        context['leitores_especiais_do_autor'] = set(leitores_especiais)

        # 12. Gerar dados PIX para widget de doação (Item 1 do ROADMAP)
        # Se o autor possui chave PIX cadastrada, gerar QR Code para doações
        # Após refatoração: PIX agora está no modelo MonetizacaoPix (OneToOne com User)
        # IMPORTANTE: QR Code sempre gerado com valor ABERTO (None)
        # O valor sugerido (pix_valor_padrao) aparece apenas como informação visual no template
        try:
            monetizacao = texto.autor.monetizacao_pix
            if monetizacao and monetizacao.tem_chave_cadastrada():
                from apps.core.utils_pix import gerar_dados_pix_completos
                try:
                    dados_pix = gerar_dados_pix_completos(
                        chave_pix=monetizacao.chave_pix,
                        tipo_chave=monetizacao.tipo_chave_pix,
                        nome_beneficiario=monetizacao.pix_nome_completo,
                        nome_banco=monetizacao.pix_nome_banco,
                        valor=None,  # Sempre valor aberto - usuário define o valor no app do banco
                        descricao="DOACAO LIVREDIA"  # Identificação da doação no app do banco
                    )
                    context['qrcode_base64'] = dados_pix['qrcode_base64']
                    context['pix_payload'] = dados_pix['payload']  # PIX Copia e Cola
                except Exception as e:
                    # Log do erro mas não quebrar a página (widget simplesmente não aparece)
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Erro ao gerar QR Code PIX para autor {texto.autor.id}: {str(e)}")
                    context['qrcode_base64'] = None
        except Exception:
            # Monetização PIX não existe para este autor (DoesNotExist)
            pass

        # 13. Verificação de idade para conteúdo sensível (is_maioridade)
        # Controla a exibição do texto para maiores de 18 anos
        context['requer_maioridade'] = texto.is_maioridade
        context['usuario_menor_18'] = False
        context['mostrar_modal_confirmacao'] = False
        context['data_nascimento_formatada'] = ''

        if texto.is_maioridade:
            if self.request.user.is_authenticated:
                # Usuário está logado - verificar idade
                if self.request.user.data_nascimento:
                    from datetime import date
                    hoje = date.today()
                    # Calcular idade considerando dia e mês de nascimento
                    idade = hoje.year - self.request.user.data_nascimento.year - (
                        (hoje.month, hoje.day) < (self.request.user.data_nascimento.month, self.request.user.data_nascimento.day)
                    )

                    if idade < 18:
                        # Menor de 18 - não pode ver o texto
                        context['usuario_menor_18'] = True
                    else:
                        # Maior de 18 - verificar se deve mostrar modal
                        # MELHORIA 73: Verificar se usuário já optou por não ver avisos
                        try:
                            config = self.request.user.configuracao
                            mostrar_avisos = config.mostrar_aviso_maioridade
                        except:
                            mostrar_avisos = True  # Padrão: mostrar avisos

                        # Só mostrar modal se mostrar_aviso_maioridade == True
                        if mostrar_avisos:
                            context['mostrar_modal_confirmacao'] = True
                            context['data_nascimento_formatada'] = self.request.user.data_nascimento.strftime('%d/%m/%Y')
                        # Se mostrar_avisos == False, modal não será exibida
                else:
                    # Usuário logado mas sem data de nascimento - tratar como menor de 18
                    context['usuario_menor_18'] = True
            # Se não está logado, o template exibirá a mensagem com botões de login/cadastro

        return context

    def post(self, request, *args, **kwargs):
        """
        Processa o formulário de comentário via HTMX.

        Retorna:
        - Sucesso: Template parcial com novo comentário (_comentario_item.html)
        - Erro: Template parcial com formulário + erros (_form_comentario.html)
        """
        self.object = self.get_object()
        texto = self.object

        # Verificar se o texto permite comentários
        if not texto.permite_comentarios:
            return HttpResponse("Comentários desabilitados para este texto.", status=403)

        # Verificar se o usuário está autenticado
        if not request.user.is_authenticated:
            return HttpResponse("Você precisa estar logado para comentar.", status=401)

        # Processar formulário
        form = ComentarioForm(request.POST)

        if form.is_valid():
            comentario = form.save(commit=False)

            # Definir campos obrigatórios
            comentario.texto = texto
            comentario.autor = request.user

            # Verificar se permite comentários anônimos
            if not texto.permite_comentarios_anonimos:
                comentario.publicado_anonimamente = False

            # Aplicar lógica de moderação
            if texto.moderacao_automatica:
                comentario.status = Comentario.Status.APROVADO
            else:
                comentario.status = Comentario.Status.PENDENTE

            comentario.save()

            # Processar menções e criar notificações (Item 2 do ROADMAP)
            from apps.comentarios.utils import processar_mencoes_comentario
            try:
                processar_mencoes_comentario(comentario)
            except Exception as e:
                # Log do erro mas não quebra o fluxo de criação do comentário
                print(f"Erro ao processar menções: {e}")

            # Retornar comentário renderizado (aprovado ou pendente)
            # O template _comentario.html já exibe mensagem amarela se for pendente
            # ETAPA 8 - Sistema de Selos: Incluir leitores especiais do autor no contexto
            leitores_especiais = AutorSeguido.objects.filter(
                autor=texto.autor,
                is_leitor_especial=True
            ).values_list('seguidor_id', flat=True)

            html = render_to_string(
                'textos/partials/_comentario_item.html',
                {
                    'comentario': comentario,
                    'texto': texto,
                    'user': request.user,
                    'leitores_especiais_do_autor': set(leitores_especiais)
                },
                request=request
            )
            return HttpResponse(html, status=200)
        else:
            # Retornar formulário com erros
            html = render_to_string(
                'textos/partials/_form_comentario.html',
                {
                    'comentario_form': form,
                    'texto': texto,
                    'permite_anonimos': texto.permite_comentarios_anonimos
                },
                request=request
            )
            return HttpResponse(html, status=400)

    def get(self, request, *args, **kwargs):
        """
        Sobrescreve GET para registrar visualização.
        Implementa reutilização inteligente de visualizações para evitar
        contabilização duplicada quando usuário abre múltiplas abas.
        """
        # Obter o objeto ANTES de renderizar (para ter acesso a self.object)
        self.object = self.get_object()

        # Registrar visualização (analytics) ANTES de renderizar
        # SEMPRE cria um novo registro para contar corretamente "Exibições totais"
        try:
            # Garantir que a sessão existe
            if not request.session.session_key:
                request.session.create()

            # Criar nova visualização a cada acesso (incluindo reloads)
            # Isso garante que "Exibições totais" conte todos os acessos
            # "Visualizações únicas" será calculado com Count(distinct sessao_id)
            self.visualizacao_atual = Visualizacao.objects.create(
                texto=self.object,
                usuario=request.user if request.user.is_authenticated else None,
                ip_address=get_client_ip(request),
                sessao_id=request.session.session_key
            )
        except Exception as e:
            # Se houver erro ao registrar visualização, apenas logar (não quebrar a página)
            print(f"Erro ao registrar visualização: {e}")
            self.visualizacao_atual = None

        # Agora renderizar o template (que vai chamar get_context_data com self.visualizacao_atual já definido)
        return super().get(request, *args, **kwargs)


@login_required
@require_http_methods(["DELETE", "POST"])
def deletar_comentario(request, comentario_id):
    """
    View para deletar comentário.

    Regras:
    - Apenas o autor do comentário pode deletar
    - Funciona para comentários anônimos também (verifica autor no backend)
    - Funciona para comentários pendentes ou aprovados
    - Remove da tela via HTMX (sem reload)
    """
    comentario = get_object_or_404(Comentario, id=comentario_id)

    # Verificar se o usuário é o autor do comentário
    if comentario.autor != request.user:
        return HttpResponse("Você não tem permissão para excluir este comentário.", status=403)

    # Deletar o comentário (respostas serão deletadas em cascata se configurado)
    comentario.delete()

    # Retornar resposta vazia (HTMX vai remover o elemento da tela)
    return HttpResponse("", status=200)


class AcervoTextos(ListView):
    """
    View para listagem completa do acervo de textos (Tela 9).

    Funcionalidades:
    - Lista todos os textos publicados
    - Filtros combinados (autor, título, tag, data)
    - Ordenação (mais recentes, menos recentes, mais views, autor alfabético)
    - Paginação configurável (30, 50, 100 textos por página)
    - Interatividade HTMX para filtros e paginação
    - Contador de resultados encontrados
    - Preview de 300 caracteres do conteúdo
    - Display de avatar, nome do autor, tags, views

    Baseada na especificação: guidelines_projeto.txt (Tela 3: Acervo de Textos)
    """
    model = Texto
    template_name = 'textos/acervo.html'
    context_object_name = 'textos'
    paginate_by = 30  # Padrão: 30 textos por página

    def get_queryset(self):
        """
        Retorna queryset de textos publicados com filtros e ordenação.

        Filtros combinados (GET parameters):
        - autor: ID do autor
        - titulo: busca parcial case-insensitive
        - tag: slug da tag
        - data_inicio: data inicial (YYYY-MM-DD)
        - data_fim: data final (YYYY-MM-DD)

        Ordenação (GET parameter 'ordenar'):
        - 'recentes' (padrão): -data_publicacao
        - 'antigos': data_publicacao
        - 'views': -total_views (anotar contagem de visualizações)
        - 'autor': autor__first_name
        """
        # IMPORTANTE: Exclui textos suspensos e textos de autores suspensos
        queryset = Texto.objects.filter(
            status=Texto.Status.PUBLICADO,
            is_suspended=False,  # Ocultar textos suspensos
            autor__is_suspended=False  # Ocultar textos de autores suspensos
        )

        # Otimização: select_related para autor, prefetch_related para tags
        queryset = queryset.select_related('autor').prefetch_related('tags')

        # Anotar contagem de visualizações para ordenação e display
        queryset = queryset.annotate(total_views=Count('visualizacoes'))

        # Anotar se o usuário logado está seguindo o autor de cada texto (Item 3.3 do ROADMAP)
        if self.request.user.is_authenticated:
            from django.db.models import Exists, OuterRef
            queryset = queryset.annotate(
                seguindo_autor=Exists(
                    AutorSeguido.objects.filter(
                        seguidor=self.request.user,
                        autor=OuterRef('autor')
                    )
                )
            )
        else:
            # Usuário não logado: nenhum autor está sendo seguido
            from django.db.models import Value
            queryset = queryset.annotate(seguindo_autor=Value(False))

        # Anotar se o usuário logado salvou cada texto para ler mais tarde (Item 4.2 do ROADMAP)
        if self.request.user.is_authenticated:
            from django.db.models import Exists, OuterRef
            queryset = queryset.annotate(
                na_lista_leitura=Exists(
                    TextoLeituraPosterior.objects.filter(
                        usuario=self.request.user,
                        texto=OuterRef('pk')
                    )
                )
            )
        else:
            # Usuário não logado: nenhum texto está na lista
            from django.db.models import Value
            queryset = queryset.annotate(na_lista_leitura=Value(False))

        # ===== FILTROS =====

        # Filtro por autor
        autor_id = self.request.GET.get('autor')
        if autor_id:
            try:
                queryset = queryset.filter(autor_id=int(autor_id))
            except ValueError:
                pass  # ID inválido, ignora filtro

        # Filtro por título (busca parcial, case-insensitive)
        titulo = self.request.GET.get('titulo', '').strip()
        if titulo:
            queryset = queryset.filter(titulo__icontains=titulo)

        # Filtro por tag
        tag_slug = self.request.GET.get('tag', '').strip()
        if tag_slug:
            queryset = queryset.filter(tags__slug=tag_slug)

        # Filtro por data (intervalo)
        data_inicio = self.request.GET.get('data_inicio', '').strip()
        data_fim = self.request.GET.get('data_fim', '').strip()
        if data_inicio:
            from datetime import datetime
            try:
                data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                queryset = queryset.filter(data_publicacao__date__gte=data_inicio_obj)
            except ValueError:
                pass  # Data inválida, ignora filtro
        if data_fim:
            from datetime import datetime
            try:
                data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
                queryset = queryset.filter(data_publicacao__date__lte=data_fim_obj)
            except ValueError:
                pass  # Data inválida, ignora filtro

        # Filtro por pseudônimo
        # Mostra apenas textos onde autor escolheu usar pseudônimo (display_autoria = 'PSEUDONIMO')
        pseudonimo_id = self.request.GET.get('pseudonimo')
        if pseudonimo_id:
            try:
                queryset = queryset.filter(
                    autor_id=int(pseudonimo_id),
                    display_autoria=Texto.DisplayAutoria.PSEUDONIMO
                )
            except ValueError:
                pass  # ID inválido, ignora filtro

        # ===== ORDENAÇÃO =====

        ordenar = self.request.GET.get('ordenar', 'recentes')
        if ordenar == 'antigos':
            queryset = queryset.order_by('data_publicacao')
        elif ordenar == 'views':
            queryset = queryset.order_by('-total_views', '-data_publicacao')
        elif ordenar == 'autor':
            queryset = queryset.order_by('autor__first_name', 'autor__last_name', '-data_publicacao')
        else:  # 'recentes' (padrão)
            queryset = queryset.order_by('-data_publicacao')

        return queryset

    def get_paginate_by(self, queryset):
        """
        Retorna quantidade de itens por página (configurável via GET parameter).

        Valores permitidos: 30, 50, 100
        Padrão: 30
        """
        per_page = self.request.GET.get('per_page', '30')
        try:
            per_page = int(per_page)
            if per_page not in [30, 50, 100]:
                per_page = 30
        except ValueError:
            per_page = 30
        return per_page

    def get_context_data(self, **kwargs):
        """
        Adiciona dados extras ao contexto:
        - Lista de autores (para filtro)
        - Lista de tags (para filtro)
        - Contador de resultados
        - Parâmetros de filtros ativos (para manter no form)
        """
        context = super().get_context_data(**kwargs)

        # 1. Lista de autores (para dropdown de filtro)
        # Apenas autores NÃO SUSPENSOS que têm textos publicados e não suspensos
        autores = User.objects.filter(
            role=User.Role.AUTOR,
            is_suspended=False,  # Ocultar autores suspensos do dropdown
            textos__status=Texto.Status.PUBLICADO,
            textos__is_suspended=False  # Ocultar textos suspensos
        ).distinct().order_by('first_name', 'last_name')
        context['autores'] = autores

        # 2. Lista de tags (para dropdown de filtro)
        # Apenas tags que têm textos publicados, não suspensos e de autores não suspensos
        from apps.textos.models import Tag
        tags = Tag.objects.filter(
            textos__status=Texto.Status.PUBLICADO,
            textos__is_suspended=False,  # Excluir textos suspensos
            textos__autor__is_suspended=False  # Excluir textos de autores suspensos
        ).distinct().annotate(
            num_textos=Count('textos', filter=Q(
                textos__status=Texto.Status.PUBLICADO,
                textos__is_suspended=False,
                textos__autor__is_suspended=False
            ))
        ).order_by('-num_textos', 'nome')[:20]  # Top 20 tags mais usadas
        context['tags'] = tags

        # 2b. Lista de autores com pseudônimos (para dropdown de filtro de pseudônimo)
        # Apenas autores NÃO SUSPENSOS que têm pseudônimo cadastrado E têm textos publicados e não suspensos com display_autoria='PSEUDONIMO'
        pseudonimos = User.objects.filter(
            role=User.Role.AUTOR,
            is_suspended=False,  # Ocultar autores suspensos do dropdown
            textos__status=Texto.Status.PUBLICADO,
            textos__is_suspended=False,  # Ocultar textos suspensos
            textos__display_autoria=Texto.DisplayAutoria.PSEUDONIMO
        ).exclude(pseudonimo__isnull=True).exclude(pseudonimo='').distinct().order_by('pseudonimo')
        context['pseudonimos'] = pseudonimos

        # 3. Contador de resultados (usa o paginator para pegar o total correto)
        if context.get('paginator'):
            context['total_resultados'] = context['paginator'].count
        else:
            context['total_resultados'] = self.get_queryset().count()

        # 4. Parâmetros de filtros ativos (para manter no form e exibir)
        context['filtro_autor'] = self.request.GET.get('autor', '')
        context['filtro_titulo'] = self.request.GET.get('titulo', '')
        context['filtro_tag'] = self.request.GET.get('tag', '')
        context['filtro_pseudonimo'] = self.request.GET.get('pseudonimo', '')
        context['filtro_data_inicio'] = self.request.GET.get('data_inicio', '')
        context['filtro_data_fim'] = self.request.GET.get('data_fim', '')
        context['ordenar'] = self.request.GET.get('ordenar', 'recentes')
        context['per_page'] = self.get_paginate_by(None)

        # 5. Verificar se há filtros ativos (para mostrar botão "Limpar Filtros")
        filtros_ativos = bool(
            context['filtro_autor'] or
            context['filtro_titulo'] or
            context['filtro_tag'] or
            context['filtro_pseudonimo'] or
            context['filtro_data_inicio'] or
            context['filtro_data_fim'] or
            context['ordenar'] != 'recentes' or
            context['per_page'] != 30
        )
        context['filtros_ativos'] = filtros_ativos

        return context

    def render_to_response(self, context, **response_kwargs):
        """
        Se for requisição HTMX, retorna apenas o fragmento da lista.
        Caso contrário, retorna a página completa.
        """
        if self.request.headers.get('HX-Request'):
            # Requisição HTMX: retornar apenas o fragmento da lista
            return render(
                self.request,
                'textos/partials/_lista_textos.html',
                context,
                **response_kwargs
            )
        else:
            # Requisição normal: retornar página completa
            return super().render_to_response(context, **response_kwargs)


class GaleriaAutores(ListView):
    """
    View para exibir galeria de autores com filtros.

    Tela 10 - FASE 2: ZONA PÚBLICA - CONTEÚDO
    Baseada no protótipo: prototipos_telas/galeria_de_autores/code.html

    Exibe:
    - Grid de autores verificados (role=AUTOR)
    - Filtro por tema/tag
    - Informações: avatar, nome/pseudônimo, bio, total de textos, total de visualizações
    - Botões: Ver textos do autor, Falar com autor (futuro)
    - HTMX para filtros assíncronos
    """
    model = User
    template_name = 'textos/galeria_autores.html'
    context_object_name = 'autores'
    paginate_by = 100  # 100 autores por página

    def get_queryset(self):
        """
        Retorna queryset de autores ativos com anotações de textos e visualizações.
        Suporta filtro por tema/tag (?tag=slug).
        """
        # Base: todos os autores ativos e NÃO suspensos
        # IMPORTANTE: Exclui autores suspensos da galeria
        queryset = User.objects.filter(
            role=User.Role.AUTOR,
            is_active=True,
            is_suspended=False  # Ocultar autores suspensos
        )

        # Anotar contagem de textos publicados (excluindo textos suspensos)
        queryset = queryset.annotate(
            total_textos=Count(
                'textos',
                filter=Q(textos__status=Texto.Status.PUBLICADO) & Q(textos__is_suspended=False),
                distinct=True
            )
        )

        # Anotar contagem de visualizações (soma de todas as views dos textos do autor, excluindo textos suspensos)
        queryset = queryset.annotate(
            total_visualizacoes=Count(
                'textos__visualizacoes',
                filter=Q(textos__status=Texto.Status.PUBLICADO) & Q(textos__is_suspended=False),
                distinct=True
            )
        )

        # Anotar se o usuário logado está seguindo cada autor (Item 3.4 do ROADMAP)
        if self.request.user.is_authenticated:
            from django.db.models import Exists, OuterRef
            queryset = queryset.annotate(
                seguindo_autor=Exists(
                    AutorSeguido.objects.filter(
                        seguidor=self.request.user,
                        autor=OuterRef('pk')
                    )
                )
            )
        else:
            # Usuário não logado: nenhum autor está sendo seguido
            from django.db.models import Value
            queryset = queryset.annotate(seguindo_autor=Value(False))

        # Filtro por temas/tags múltiplas (?tags=slug1&tags=slug2)
        filtro_tags = self.request.GET.getlist('tags')
        if filtro_tags:
            # Filtrar autores que têm textos publicados (não suspensos) com QUALQUER uma dessas tags
            queryset = queryset.filter(
                textos__tags__slug__in=filtro_tags,
                textos__status=Texto.Status.PUBLICADO,
                textos__is_suspended=False  # Excluir textos suspensos
            ).distinct()

        # Filtro por nome do autor (?busca_nome=texto)
        busca_nome = self.request.GET.get('busca_nome', '').strip()
        if busca_nome:
            # Buscar em first_name, last_name ou pseudonimo (case-insensitive, busca parcial)
            queryset = queryset.filter(
                Q(first_name__icontains=busca_nome) |
                Q(last_name__icontains=busca_nome) |
                Q(pseudonimo__icontains=busca_nome)
            ).distinct()

        # Ordenação padrão: por data de cadastro (mais recentes primeiro)
        queryset = queryset.order_by('-date_joined', '-total_visualizacoes', '-total_textos')

        return queryset

    def get_context_data(self, **kwargs):
        """Adiciona contexto extra para filtros e metadados."""
        context = super().get_context_data(**kwargs)

        # Tags para o filtro (apenas tags que têm textos publicados)
        context['tags'] = Tag.objects.annotate(
            num_textos=Count('textos', filter=Q(textos__status=Texto.Status.PUBLICADO))
        ).filter(num_textos__gt=0).order_by('-num_textos', 'nome')[:20]

        # Filtros atuais
        context['filtro_tags'] = self.request.GET.getlist('tags')
        context['busca_nome'] = self.request.GET.get('busca_nome', '').strip()

        # Total de resultados (usa o paginator para pegar o total correto)
        if context.get('paginator'):
            context['total_resultados'] = context['paginator'].count
        else:
            context['total_resultados'] = self.get_queryset().count()

        # Flag para indicar se há filtros ativos
        context['filtros_ativos'] = bool(context['filtro_tags'] or context['busca_nome'])

        return context

    def render_to_response(self, context, **response_kwargs):
        """
        Retorna partial template para requisições HTMX,
        ou página completa para requisições normais.
        """
        if self.request.headers.get('HX-Request'):
            # Requisição HTMX: retornar apenas o grid de autores
            return HttpResponse(
                render_to_string(
                    'textos/partials/_grid_autores.html',
                    context,
                    request=self.request
                )
            )
        else:
            # Requisição normal: retornar página completa
            return super().render_to_response(context, **response_kwargs)


@csrf_exempt
@require_http_methods(["POST"])
def atualizar_tempo_leitura(request):
    """
    API endpoint para atualizar tempo de leitura via JavaScript heartbeat.

    Recebe:
    - visualizacao_id: ID da visualização
    - tempo_segundos: Tempo acumulado em segundos

    Retorna:
    - JSON com status de sucesso ou erro
    """
    try:
        # Parse do JSON
        data = json.loads(request.body)
        visualizacao_id = data.get('visualizacao_id')
        tempo_segundos = data.get('tempo_segundos')

        # Validações
        if not visualizacao_id:
            return JsonResponse({'success': False, 'error': 'visualizacao_id obrigatório'}, status=400)

        if tempo_segundos is None or tempo_segundos < 0:
            return JsonResponse({'success': False, 'error': 'tempo_segundos inválido'}, status=400)

        # Buscar visualização
        try:
            visualizacao = Visualizacao.objects.get(id=visualizacao_id)
        except Visualizacao.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Visualização não encontrada'}, status=404)

        # Atualizar tempo de leitura (acumular)
        # Se já existe tempo, acumula; senão, define o novo valor
        if visualizacao.tempo_permanencia:
            visualizacao.tempo_permanencia += int(tempo_segundos)
        else:
            visualizacao.tempo_permanencia = int(tempo_segundos)

        # Salvar (NÃO atualiza data_visualizacao conforme Opção B)
        visualizacao.save(update_fields=['tempo_permanencia'])

        return JsonResponse({
            'success': True,
            'tempo_total': visualizacao.tempo_permanencia
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception as e:
        print(f"Erro ao atualizar tempo de leitura: {e}")
        return JsonResponse({'success': False, 'error': 'Erro interno'}, status=500)


@require_http_methods(["GET"])
def buscar_usuarios_mencao(request):
    """
    Endpoint AJAX para buscar usuários para menção em comentários.

    Busca usuários por username (case-insensitive) para autocomplete
    no sistema de menções (@username).

    Query params:
        q (str): Termo de busca (username parcial ou completo)

    Returns:
        JsonResponse: Lista de usuários encontrados
        {
            "usuarios": [
                {
                    "username": "ciniro",
                    "nome_completo": "Ciniro Silva",
                    "avatar_url": "https://..."
                }
            ]
        }

    Example:
        GET /texto/api/usuarios/buscar/?q=cin
        →  retorna usuários cujo username contém "cin"

    Note:
        - Máximo de 10 resultados
        - Apenas usuários não suspensos
        - Ordenação alfabética por username
        - Busca é case-insensitive
    """
    from django.db.models import Case, When, IntegerField

    termo = request.GET.get('q', '').strip()

    # Buscar usuários (max 10 resultados)
    # Ordenação: primeiro não-admins alfabeticamente, depois admins alfabeticamente
    usuarios = User.objects.filter(
        username__icontains=termo,
        is_suspended=False
    ).annotate(
        ordem_admin=Case(
            When(role='ADMIN', then=1),  # Admins vão para o final
            default=0,  # Outros ficam no início
            output_field=IntegerField(),
        )
    ).order_by('ordem_admin', 'username')[:10]

    # Serializar para JSON
    resultado = {
        "usuarios": [
            {
                "username": u.username,
                "nome_completo": u.get_full_name() or u.username,
                "avatar_url": u.get_avatar_url(),
                "role": u.role,
                "is_admin": u.is_admin
            }
            for u in usuarios
        ]
    }

    return JsonResponse(resultado)


@login_required
@require_POST
def salvar_configuracao_leitura(request):
    """
    API endpoint para salvar configurações de leitura via AJAX.
    
    Salva no banco de dados as preferências do usuário logado:
    - nivel_zoom: nível de zoom (1-10)
    - tema: tema de leitura (padrao, sepia, noturno, jornal, crt, eink)
    
    Endpoint: POST /texto/api/salvar-config-leitura/
    Item 3.2 do ROADMAP
    
    POST params:
        nivel_zoom (optional): int 1-10
        tema (optional): str (padrao, sepia, noturno, jornal, crt, eink)
    
    Returns:
        JSON: {"success": True} ou {"success": False, "error": "mensagem"}
    
    Example:
        POST /texto/api/salvar-config-leitura/
        Body: nivel_zoom=7&tema=sepia
        → salva configurações e retorna {"success": true}
    
    Note:
        - Requer autenticação (@login_required)
        - Usa objeto ConfiguracaoUsuario do usuário logado
        - Validações aplicadas pelo modelo
    """
    try:
        config = request.user.configuracao
        
        # Salvar nível de zoom (se fornecido)
        nivel_zoom = request.POST.get('nivel_zoom')
        if nivel_zoom:
            nivel_zoom = int(nivel_zoom)
            # Validar range 1-10
            if 1 <= nivel_zoom <= 10:
                config.nivel_zoom_padrao = nivel_zoom
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Nível de zoom deve estar entre 1 e 10'
                }, status=400)
        
        # Salvar tema (se fornecido)
        tema = request.POST.get('tema')
        if tema:
            # Validar tema válido
            temas_validos = ['padrao', 'sepia', 'noturno', 'jornal', 'crt', 'eink']
            if tema in temas_validos:
                config.tema_leitura_padrao = tema
            else:
                return JsonResponse({
                    'success': False,
                    'error': f'Tema inválido. Temas válidos: {", ".join(temas_validos)}'
                }, status=400)
        
        # Salvar no banco
        config.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ============================================================================
# VIEWS DE DOWNLOAD (Item 3.5 do ROADMAP)
# ============================================================================

def download_pdf_texto(request, pk):
    """
    Gera e baixa PDF do texto com informações de citação.

    Item 3.5.1 do ROADMAP:
    - Nome do autor (real, pseudônimo ou ambos)
    - Título e subtítulo
    - Data de publicação
    - Conteúdo do texto
    - Mensagem de propriedade e citação
    """
    texto = get_object_or_404(Texto, pk=pk, status='PUBLICADO')

    # Criar buffer de memória
    buffer = BytesIO()

    # Criar documento PDF
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    # Container para os elementos do PDF
    story = []

    # Estilos
    styles = getSampleStyleSheet()

    # Estilo para título
    style_titulo = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor='#e69019',  # Laranja do sistema
        spaceAfter=12,
        alignment=TA_CENTER,
    )

    # Estilo para subtítulo
    style_subtitulo = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor='#4F4A45',  # Sépia
        spaceAfter=12,
        alignment=TA_CENTER,
    )

    # Estilo para autor
    style_autor = ParagraphStyle(
        'CustomAuthor',
        parent=styles['Normal'],
        fontSize=12,
        textColor='#3A4D39',  # Verde floresta
        spaceAfter=6,
        alignment=TA_CENTER,
    )

    # Estilo para data
    style_data = ParagraphStyle(
        'CustomDate',
        parent=styles['Normal'],
        fontSize=10,
        textColor='#666666',
        spaceAfter=20,
        alignment=TA_CENTER,
    )

    # Estilo para conteúdo
    style_conteudo = ParagraphStyle(
        'CustomContent',
        parent=styles['BodyText'],
        fontSize=11,
        leading=16,
        alignment=TA_JUSTIFY,
        spaceAfter=12,
    )

    # Estilo para rodapé
    style_rodape = ParagraphStyle(
        'CustomFooter',
        parent=styles['Normal'],
        fontSize=9,
        textColor='#666666',
        leading=12,
        spaceAfter=6,
        alignment=TA_CENTER,
    )

    # Adicionar título
    story.append(Paragraph(texto.titulo, style_titulo))

    # Adicionar subtítulo (se houver)
    if texto.subtitulo:
        story.append(Paragraph(texto.subtitulo, style_subtitulo))

    # Nome do autor baseado na configuração de exibição
    if texto.display_autoria == 'REAL':
        nome_autor = texto.autor.get_full_name()
    elif texto.display_autoria == 'PSEUDONIMO':
        nome_autor = texto.autor.pseudonimo or texto.autor.get_full_name()
    else:  # AMBOS
        if texto.autor.pseudonimo:
            nome_autor = f"{texto.autor.get_full_name()} ({texto.autor.pseudonimo})"
        else:
            nome_autor = texto.autor.get_full_name()

    story.append(Paragraph(f"<b>Por:</b> {nome_autor}", style_autor))

    # Data de publicação
    if texto.data_publicacao:
        # Dicionário de tradução de meses para português
        meses_pt = {
            'January': 'janeiro', 'February': 'fevereiro', 'March': 'março',
            'April': 'abril', 'May': 'maio', 'June': 'junho',
            'July': 'julho', 'August': 'agosto', 'September': 'setembro',
            'October': 'outubro', 'November': 'novembro', 'December': 'dezembro'
        }
        # Formatar data com mês em inglês primeiro
        data_formatada = texto.data_publicacao.strftime("%d de %B de %Y")
        # Substituir mês em inglês pelo português
        for mes_en, mes_pt in meses_pt.items():
            data_formatada = data_formatada.replace(mes_en, mes_pt)
        story.append(Paragraph(f"<i>Publicado em {data_formatada}</i>", style_data))

    story.append(Spacer(1, 0.5*cm))

    # Limpar HTML do conteúdo e adicionar
    # Remove tags HTML mas mantém quebras de linha
    conteudo_limpo = re.sub(r'<br\s*/?>', '\n', texto.conteudo)
    conteudo_limpo = re.sub(r'<p>', '', conteudo_limpo)
    conteudo_limpo = re.sub(r'</p>', '\n', conteudo_limpo)
    conteudo_limpo = re.sub(r'<[^>]+>', '', conteudo_limpo)

    # Adicionar parágrafos
    for paragrafo in conteudo_limpo.split('\n'):
        if paragrafo.strip():
            story.append(Paragraph(paragrafo.strip(), style_conteudo))

    # Adicionar separador
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("_" * 80, style_rodape))
    story.append(Spacer(1, 0.5*cm))

    # Mensagem de propriedade
    mensagem_propriedade = (
        "Este texto é propriedade do autor e publicado na Plataforma Livre Dia "
        "conforme Termos de Uso e Responsabilidades."
    )
    story.append(Paragraph(mensagem_propriedade, style_rodape))

    # Adicionar URL
    url = f"https://livredia.com.br/texto/{texto.pk}/"
    story.append(Paragraph(f"<b>Disponível em:</b> {url}", style_rodape))

    # Gerar PDF
    doc.build(story)

    # Obter PDF do buffer
    pdf = buffer.getvalue()
    buffer.close()

    # Criar response
    response = HttpResponse(pdf, content_type='application/pdf')
    filename = f"{texto.titulo[:50].replace(' ', '_')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response


def download_bibtex_texto(request, pk):
    """
    Gera e baixa arquivo .txt com referência em formato BibTeX.

    Item 3.5.2 do ROADMAP:
    Formato baseado em contexto_projeto/exemplos_citacao/exemplo_citacao.txt
    """
    texto = get_object_or_404(Texto, pk=pk, status='PUBLICADO')

    # Nome do autor baseado na configuração
    if texto.display_autoria == 'REAL':
        nome_autor = texto.autor.get_full_name()
    elif texto.display_autoria == 'PSEUDONIMO':
        nome_autor = texto.autor.pseudonimo or texto.autor.get_full_name()
    else:  # AMBOS
        if texto.autor.pseudonimo:
            nome_autor = f"{texto.autor.get_full_name()} ({texto.autor.pseudonimo})"
        else:
            nome_autor = texto.autor.get_full_name()

    # Gerar chave da referência (sobrenome_titulo_ano)
    sobrenome = texto.autor.last_name.lower().replace(' ', '_')
    titulo_curto = texto.titulo[:20].lower().replace(' ', '_')
    ano = texto.data_publicacao.year if texto.data_publicacao else datetime.now().year
    chave = f"{sobrenome}_{titulo_curto}_{ano}"

    # Data de publicação
    data_pub = texto.data_publicacao.strftime("%Y-%m-%d") if texto.data_publicacao else datetime.now().strftime("%Y-%m-%d")

    # Data de acesso (hoje)
    data_acesso = datetime.now().strftime("%Y-%m-%d")

    # URL do texto
    url = f"https://livredia.com.br/texto/{texto.pk}/"

    # Montar conteúdo BibTeX
    conteudo = f"""@online{{{chave},
  author       = {{{nome_autor}}},
  title        = {{{texto.titulo}}},"""

    # Adicionar subtítulo se houver
    if texto.subtitulo:
        conteudo += f"""
  subtitle     = {{{texto.subtitulo}}},"""

    conteudo += f"""
  date         = {{{data_pub}}},
  organization = {{Plataforma Livre Dia}},
  url          = {{{url}}},
  urldate      = {{{data_acesso}}}
}}
"""

    # Criar response
    response = HttpResponse(conteudo, content_type='text/plain; charset=utf-8')
    filename = f"{texto.titulo[:50].replace(' ', '_')}_bibtex.txt"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response


def download_abnt_texto(request, pk):
    """
    Gera e baixa arquivo .txt com referência em formato ABNT.

    Item 3.5.3 do ROADMAP:
    Formato baseado em contexto_projeto/exemplos_citacao/exemplo_citacao.txt
    Formato: SOBRENOME, Nome. **Título**: Subtítulo. Nome do Site, data. Disponível em: <url>. Acesso em: data.
    """
    texto = get_object_or_404(Texto, pk=pk, status='PUBLICADO')

    # Nome do autor
    sobrenome = texto.autor.last_name.upper()
    nome = texto.autor.first_name

    # Se tiver pseudônimo e display_autoria for PSEUDONIMO ou AMBOS
    if texto.display_autoria == 'PSEUDONIMO' and texto.autor.pseudonimo:
        # Usar pseudônimo
        partes_pseudonimo = texto.autor.pseudonimo.split()
        if len(partes_pseudonimo) > 1:
            sobrenome = partes_pseudonimo[-1].upper()
            nome = ' '.join(partes_pseudonimo[:-1])
        else:
            sobrenome = texto.autor.pseudonimo.upper()
            nome = ""
    elif texto.display_autoria == 'AMBOS' and texto.autor.pseudonimo:
        # Mostrar ambos
        nome = f"{texto.autor.first_name} ({texto.autor.pseudonimo})"

    # Título em negrito (usando convenção de markdown/texto)
    titulo = texto.titulo

    # Subtítulo (se houver, com : antes)
    if texto.subtitulo:
        referencia = f"{sobrenome}, {nome}. **{titulo}: {texto.subtitulo}**."
    else:
        referencia = f"{sobrenome}, {nome}. **{titulo}**."

    # Nome do site
    referencia += " Plataforma Livre Dia"

    # Data de publicação
    if texto.data_publicacao:
        # Formatar mês em português (abreviado em minúsculas)
        meses = {
            'Jan': 'jan.', 'Feb': 'fev.', 'Mar': 'mar.', 'Apr': 'abr.',
            'May': 'maio', 'Jun': 'jun.', 'Jul': 'jul.', 'Aug': 'ago.',
            'Sep': 'set.', 'Oct': 'out.', 'Nov': 'nov.', 'Dec': 'dez.'
        }
        data_str = texto.data_publicacao.strftime("%d %b %Y")  # Sem ponto após %b
        for en, pt in meses.items():
            data_str = data_str.replace(en, pt)
        referencia += f", {data_str}."

    # URL
    url = f"https://livredia.com.br/texto/{texto.pk}/"
    referencia += f" Disponível em: <{url}>."

    # Data de acesso
    meses = {
        'Jan': 'jan.', 'Feb': 'fev.', 'Mar': 'mar.', 'Apr': 'abr.',
        'May': 'maio', 'Jun': 'jun.', 'Jul': 'jul.', 'Aug': 'ago.',
        'Sep': 'set.', 'Oct': 'out.', 'Nov': 'nov.', 'Dec': 'dez.'
    }
    acesso_str = datetime.now().strftime("%d %b %Y")  # Sem ponto após %b
    for en, pt in meses.items():
        acesso_str = acesso_str.replace(en, pt)
    referencia += f" Acesso em: {acesso_str}."

    # Criar response
    response = HttpResponse(referencia, content_type='text/plain; charset=utf-8')
    filename = f"{texto.titulo[:50].replace(' ', '_')}_abnt.txt"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response


# ============================================================================
# CARTÃO DA BIBLIOTECA - Item 3.6 do ROADMAP
# ============================================================================
# Resgata a experiência nostálgica dos antigos cartões de controle de
# empréstimo de bibliotecas físicas, onde leitores deixavam suas assinaturas
# demonstrando apreço pelos livros que tocaram seus corações.
# ============================================================================


@require_POST
@login_required
def assinar_cartao(request, pk):
    """
    Permite que um usuário logado assine o cartão da biblioteca de um texto.

    Este é um gesto de carinho e reconhecimento ao trabalho do autor,
    similar às antigas assinaturas em cartões de bibliotecas físicas.

    Funcionalidades:
    - Verifica se usuário está logado
    - Verifica se texto existe e está publicado
    - Previne assinaturas duplicadas (unique constraint)
    - Cria notificação poética para o autor
    - Retorna JSON com dados da assinatura criada

    Args:
        request: HttpRequest
        pk: ID do texto

    Returns:
        JsonResponse com:
        - success: True/False
        - message: Mensagem de sucesso/erro
        - assinatura: Dados da assinatura criada (se sucesso)
    """
    try:
        # Buscar texto
        texto = get_object_or_404(Texto, pk=pk, status='PUBLICADO')

        # Verificar se usuário já assinou (proteção adicional além do unique_together)
        if CartaoBiblioteca.objects.filter(texto=texto, usuario=request.user).exists():
            return JsonResponse({
                'success': False,
                'message': '💛 Você já deixou sua marca neste cartão. Sua assinatura está preservada para sempre!'
            }, status=400)

        # Criar assinatura
        assinatura = CartaoBiblioteca.objects.create(
            texto=texto,
            usuario=request.user
        )

        # Criar notificação poética para o autor
        # Texto: "@username deixou sua assinatura no cartão da biblioteca do texto "Título". Um leitor tocado por suas palavras! 💛"
        texto_notificacao = (
            f"@{request.user.username} deixou sua assinatura no cartão da biblioteca "
            f"do texto \"{texto.titulo}\". Um leitor tocado por suas palavras! 💛"
        )

        criar_notificacao(
            motivo_codigo='ASSINATURA_CARTAO',
            usuario_origem=request.user,
            usuario_destino=texto.autor,
            texto=texto_notificacao,
            link_destino=f'/texto/{texto.pk}/'
        )

        # Preparar dados da assinatura para retornar
        # Incluir cidade/país se disponíveis
        localizacao = []
        if request.user.cidade:
            localizacao.append(request.user.cidade)
        if request.user.pais:
            localizacao.append(request.user.pais)
        localizacao_str = ", ".join(localizacao) if localizacao else ""

        assinatura_data = {
            'id': assinatura.id,
            'nome_completo': request.user.get_full_name(),
            'username': request.user.username,
            'localizacao': localizacao_str,
            'data_assinatura': assinatura.data_assinatura.isoformat(),
            'is_current_user': True
        }

        return JsonResponse({
            'success': True,
            'message': '✍️ Sua assinatura foi registrada com carinho! O autor saberá que este texto encontrou lar em seu coração.',
            'assinatura': assinatura_data
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Ocorreu um erro ao registrar sua assinatura. Por favor, tente novamente.'
        }, status=500)


def listar_assinaturas(request, pk):
    """
    Lista todas as assinaturas do cartão da biblioteca de um texto.

    Endpoint público (não requer login) que retorna todas as assinaturas
    em ordem cronológica, como nos antigos cartões de biblioteca.

    Args:
        request: HttpRequest
        pk: ID do texto

    Returns:
        JsonResponse com:
        - total: Número total de assinaturas
        - assinaturas: Lista de assinaturas (ordem cronológica)
        - usuario_assinou: True se usuário logado já assinou
    """
    try:
        # Buscar texto
        texto = get_object_or_404(Texto, pk=pk, status='PUBLICADO')

        # Buscar todas as assinaturas em ordem cronológica
        assinaturas = CartaoBiblioteca.objects.filter(texto=texto).select_related('usuario')

        # Verificar se usuário logado já assinou
        usuario_assinou = False
        if request.user.is_authenticated:
            usuario_assinou = assinaturas.filter(usuario=request.user).exists()

        # Preparar lista de assinaturas
        assinaturas_list = []
        for assinatura in assinaturas:
            # Incluir cidade/país se disponíveis
            localizacao = []
            if assinatura.usuario.cidade:
                localizacao.append(assinatura.usuario.cidade)
            if assinatura.usuario.pais:
                localizacao.append(assinatura.usuario.pais)
            localizacao_str = ", ".join(localizacao) if localizacao else ""

            assinaturas_list.append({
                'id': assinatura.id,
                'nome_completo': assinatura.usuario.get_full_name(),
                'username': assinatura.usuario.username,
                'localizacao': localizacao_str,
                'data_assinatura': assinatura.data_assinatura.isoformat(),
                'is_current_user': request.user.is_authenticated and assinatura.usuario == request.user
            })

        return JsonResponse({
            'total': assinaturas.count(),
            'assinaturas': assinaturas_list,
            'usuario_assinou': usuario_assinou
        })

    except Exception as e:
        return JsonResponse({
            'error': 'Ocorreu um erro ao carregar as assinaturas.'
        }, status=500)


# ============================================================================
# BOTÕES DE AÇÃO RÁPIDA - Item 2.2 do ROADMAP
# ============================================================================
# Botões mobile-friendly na tela de leitura para melhorar a experiência
# do leitor: salvar nos melhores, marcar como lido, ler outro (semelhante,
# do autor, aleatório).
# ============================================================================


@login_required
@require_POST
def toggle_favorito(request, pk):
    """
    Toggle de favorito (salvar/remover dos melhores) para um texto.

    Item 2.2.1 do ROADMAP:
    Permite que leitores marquem textos como favoritos ("melhores")
    ou removam da lista de favoritos.

    Funcionalidades:
    - Verifica se usuário está logado (@login_required)
    - Verifica se texto existe e está publicado
    - Se texto já está favoritado: remove da lista
    - Se texto não está favoritado: adiciona à lista
    - Retorna JSON com novo estado

    Args:
        request: HttpRequest
        pk: ID do texto

    Returns:
        JsonResponse com:
        - success: True/False
        - favoritado: True (adicionado) ou False (removido)
        - message: Mensagem de feedback
    """
    try:
        # Buscar texto (apenas publicados)
        texto = get_object_or_404(Texto, pk=pk, status='PUBLICADO')

        # Verificar se já está favoritado
        favorito_existente = TextoFavorito.objects.filter(
            usuario=request.user,
            texto=texto
        ).first()

        if favorito_existente:
            # Já está favoritado → REMOVER
            favorito_existente.delete()
            return JsonResponse({
                'success': True,
                'favoritado': False,
                'message': 'Texto removido dos seus melhores.'
            })
        else:
            # Não está favoritado → ADICIONAR
            TextoFavorito.objects.create(
                usuario=request.user,
                texto=texto
            )

            # Criar notificação para o autor (se não for o próprio autor)
            if texto.autor != request.user:
                try:
                    criar_notificacao(
                        usuario_destino=texto.autor,
                        motivo_codigo='TEXTO_FAVORITO',
                        texto=f'@{request.user.username} salvou o texto "{texto.titulo}" em seus melhores textos.',
                        link_destino=f'/texto/{texto.pk}/',
                        usuario_origem=request.user
                    )
                except Exception as e:
                    # Falha ao criar notificação não deve impedir a ação
                    print(f"Erro ao criar notificação TEXTO_FAVORITO: {e}")

            return JsonResponse({
                'success': True,
                'favoritado': True,
                'message': 'Texto salvo nos seus melhores! 💛'
            })

    except Texto.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Texto não encontrado.'
        }, status=404)
    except Exception as e:
        print(f"Erro ao toggle favorito: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Ocorreu um erro. Por favor, tente novamente.'
        }, status=500)


@login_required
@require_POST
def toggle_lido(request, pk):
    """
    Toggle de texto lido (marcar/desmarcar como lido).

    Item 2.2.2 do ROADMAP:
    Permite que leitores marquem textos como "lidos"
    ou removam da lista de textos lidos.

    Funcionalidades:
    - Verifica se usuário está logado (@login_required)
    - Verifica se texto existe e está publicado
    - Se texto já está marcado como lido: remove da lista
    - Se texto não está marcado como lido: adiciona à lista
    - Retorna JSON com novo estado

    Args:
        request: HttpRequest
        pk: ID do texto

    Returns:
        JsonResponse com:
        - success: True/False
        - lido: True (marcado) ou False (desmarcado)
        - message: Mensagem de feedback
    """
    try:
        # Buscar texto (apenas publicados)
        texto = get_object_or_404(Texto, pk=pk, status='PUBLICADO')

        # Verificar se já está marcado como lido
        lido_existente = TextoLido.objects.filter(
            usuario=request.user,
            texto=texto
        ).first()

        if lido_existente:
            # Já está marcado como lido → REMOVER
            lido_existente.delete()
            return JsonResponse({
                'success': True,
                'lido': False,
                'message': 'Texto desmarcado como lido.'
            })
        else:
            # Não está marcado como lido → ADICIONAR
            TextoLido.objects.create(
                usuario=request.user,
                texto=texto
            )

            # Criar notificação para o autor (se não for o próprio autor)
            if texto.autor != request.user:
                try:
                    criar_notificacao(
                        usuario_destino=texto.autor,
                        motivo_codigo='TEXTO_LIDO',
                        texto=f'@{request.user.username} marcou o texto "{texto.titulo}" como lido.',
                        link_destino=f'/texto/{texto.pk}/',
                        usuario_origem=request.user
                    )
                except Exception as e:
                    # Falha ao criar notificação não deve impedir a ação
                    print(f"Erro ao criar notificação TEXTO_LIDO: {e}")

            return JsonResponse({
                'success': True,
                'lido': True,
                'message': 'Texto marcado como lido! ✓'
            })

    except Texto.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Texto não encontrado.'
        }, status=404)
    except Exception as e:
        print(f"Erro ao toggle lido: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Ocorreu um erro. Por favor, tente novamente.'
        }, status=500)


@login_required
@require_POST
def toggle_leitura_posterior(request, pk):
    """
    Toggle de leitura posterior (ler mais tarde / remover da lista).

    Item 4 do ROADMAP - Lista de Leitura:
    Permite que leitores salvem textos para ler mais tarde
    ou removam da lista de leitura.

    Funcionalidades:
    - Verifica se usuário está logado (@login_required)
    - Verifica se texto existe e está publicado
    - Se texto já está na lista: remove
    - Se texto não está na lista: adiciona
    - Retorna JSON com novo estado

    Args:
        request: HttpRequest
        pk: ID do texto

    Returns:
        JsonResponse com:
        - success: True/False
        - na_lista: True (adicionado) ou False (removido)
        - message: Mensagem de feedback
    """
    try:
        # Buscar texto (apenas publicados)
        texto = get_object_or_404(Texto, pk=pk, status='PUBLICADO')

        # Verificar se já está na lista
        leitura_existente = TextoLeituraPosterior.objects.filter(
            usuario=request.user,
            texto=texto
        ).first()

        if leitura_existente:
            # Já está na lista → REMOVER
            leitura_existente.delete()
            return JsonResponse({
                'success': True,
                'na_lista': False,
                'message': 'Texto removido da lista de leitura.'
            })
        else:
            # Não está na lista → ADICIONAR
            TextoLeituraPosterior.objects.create(
                usuario=request.user,
                texto=texto
            )

            # Criar notificação para o autor (se não for o próprio autor)
            if texto.autor != request.user:
                try:
                    criar_notificacao(
                        usuario_destino=texto.autor,
                        motivo_codigo='LER_MAIS_TARDE',
                        texto=f'@{request.user.username} adicionou o texto "{texto.titulo}" a sua lista de leitura.',
                        link_destino=f'/texto/{texto.pk}/',
                        usuario_origem=request.user
                    )
                except Exception as e:
                    # Falha ao criar notificação não deve impedir a ação
                    print(f"Erro ao criar notificação LER_MAIS_TARDE: {e}")

            return JsonResponse({
                'success': True,
                'na_lista': True,
                'message': 'Texto salvo para ler mais tarde! 📚'
            })

    except Texto.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Texto não encontrado.'
        }, status=404)
    except Exception as e:
        print(f"Erro ao toggle leitura posterior: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Ocorreu um erro. Por favor, tente novamente.'
        }, status=500)


def sorteia_texto(request, texto_atual_id, tipo_sorteio):
    """
    Sorteia um texto baseado no tipo de sorteio solicitado.

    Parâmetros:
    - texto_atual_id: ID do texto atualmente sendo visualizado
    - tipo_sorteio: 'semelhante', 'autor' ou 'aleatorio'

    Prioriza textos não lidos (se usuário logado). Se não houver textos não lidos,
    usa textos já lidos. Se não houver textos disponíveis, redireciona de volta
    com parâmetro 'sem_textos=1' para exibir modal.
    """
    # Buscar texto atual
    texto_atual = get_object_or_404(Texto, pk=texto_atual_id, status='PUBLICADO')

    # Verificar se usuário está logado (para filtrar textos lidos)
    usuario = request.user if request.user.is_authenticated else None

    # Obter IDs de textos já lidos pelo usuário
    textos_lidos_ids = []
    if usuario:
        textos_lidos_ids = list(TextoLido.objects.filter(usuario=usuario).values_list('texto_id', flat=True))

    # Variável para armazenar o texto sorteado
    texto_sorteado = None

    # TIPO 1: Ler outro semelhante (mesmas tags)
    if tipo_sorteio == 'semelhante':
        # Obter todas as tags do texto atual
        tags = texto_atual.tags.all()

        if tags.exists():
            # Buscar textos não lidos em cada tag
            for tag in tags:
                textos_candidatos = Texto.objects.filter(
                    tags=tag,
                    status='PUBLICADO'
                ).exclude(pk=texto_atual_id).distinct()

                # Filtrar textos não lidos
                if usuario and textos_lidos_ids:
                    textos_nao_lidos = textos_candidatos.exclude(pk__in=textos_lidos_ids)
                    if textos_nao_lidos.exists():
                        texto_sorteado = random.choice(list(textos_nao_lidos))
                        break
                elif textos_candidatos.exists():
                    texto_sorteado = random.choice(list(textos_candidatos))
                    break

    # TIPO 2: Ler outro do autor
    elif tipo_sorteio == 'autor':
        # Buscar textos do mesmo autor (exceto o atual)
        textos_do_autor = Texto.objects.filter(
            autor=texto_atual.autor,
            status='PUBLICADO'
        ).exclude(pk=texto_atual_id)

        # Buscar apenas textos não lidos
        if usuario and textos_lidos_ids:
            textos_nao_lidos = textos_do_autor.exclude(pk__in=textos_lidos_ids)
            if textos_nao_lidos.exists():
                texto_sorteado = random.choice(list(textos_nao_lidos))
        elif textos_do_autor.exists():
            texto_sorteado = random.choice(list(textos_do_autor))

    # TIPO 3: Ler outro aleatório
    elif tipo_sorteio == 'aleatorio':
        # Buscar qualquer texto (exceto o atual)
        todos_textos = Texto.objects.filter(status='PUBLICADO').exclude(pk=texto_atual_id)

        # Priorizar textos não lidos, mas se não houver, sortear qualquer um
        if usuario and textos_lidos_ids:
            textos_nao_lidos = todos_textos.exclude(pk__in=textos_lidos_ids)
            if textos_nao_lidos.exists():
                texto_sorteado = random.choice(list(textos_nao_lidos))
            elif todos_textos.exists():
                # Fallback: sortear qualquer texto (incluindo já lidos)
                texto_sorteado = random.choice(list(todos_textos))
        elif todos_textos.exists():
            texto_sorteado = random.choice(list(todos_textos))

    # Se encontrou um texto, redirecionar para ele
    if texto_sorteado:
        return redirect('textos:leitura_texto', pk=texto_sorteado.pk)

    # Se não encontrou nenhum texto não lido, redirecionar com parâmetro do tipo esgotado
    # (Apenas para tipos 'autor' e 'semelhante', pois 'aleatorio' já tem fallback acima)
    from django.urls import reverse
    url = reverse('textos:leitura_texto', kwargs={'pk': texto_atual_id})
    return redirect(f"{url}?tipo_esgotado={tipo_sorteio}")


def sorteia_texto_forcado(request, texto_atual_id):
    """
    Sorteia qualquer texto aleatório da plataforma (incluindo já lidos).
    Usado quando o usuário aceita sortear um texto mesmo tendo lido todos os não lidos.
    """
    # Buscar qualquer texto publicado (exceto o atual)
    todos_textos = Texto.objects.filter(status='PUBLICADO').exclude(pk=texto_atual_id)

    if todos_textos.exists():
        texto_sorteado = random.choice(list(todos_textos))
        return redirect('textos:leitura_texto', pk=texto_sorteado.pk)

    # Se não há nenhum texto além do atual, voltar para home
    return redirect('core:home')


@require_POST
def toggle_seguir_autor(request, autor_id):
    """
    Toggle de seguir/deixar de seguir um autor.

    Item 3 do ROADMAP - 'Autores seguidos':
    Permite que usuários sigam (favoritem) autores para acompanhar suas publicações.
    Usuários não logados recebem erro 401 (frontend mostra modal de login).

    Funcionalidades:
    - Verifica se usuário está logado
    - Verifica se o autor existe e tem role='AUTOR'
    - Se já está seguindo: remove da lista
    - Se não está seguindo: adiciona à lista
    - Retorna JSON com novo estado

    Args:
        request: HttpRequest
        autor_id: ID do autor (User)

    Returns:
        JsonResponse com:
        - success: True/False
        - seguindo: True (seguindo) ou False (deixou de seguir)
        - message: Mensagem de feedback
    """
    # Verificar se usuário está logado
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'requires_login': True,
            'message': 'Para seguir um autor, você precisa estar logado.'
        }, status=401)

    try:
        # Buscar autor (apenas usuários com role=AUTOR)
        autor = get_object_or_404(User, pk=autor_id, role=User.Role.AUTOR)

        # Validar: não pode seguir a si mesmo
        if request.user == autor:
            return JsonResponse({
                'success': False,
                'message': 'Você não pode seguir a si mesmo.'
            }, status=400)

        # Verificar se já está seguindo
        seguindo_existente = AutorSeguido.objects.filter(
            seguidor=request.user,
            autor=autor
        ).first()

        if seguindo_existente:
            # Já está seguindo → DEIXAR DE SEGUIR
            seguindo_existente.delete()

            # Se é requisição HTMX (para remover elemento da lista), retorna HTML vazio
            if request.headers.get('HX-Request'):
                from django.http import HttpResponse
                return HttpResponse(status=200)

            # Caso contrário, retorna JSON (compatibilidade com outras funcionalidades)
            return JsonResponse({
                'success': True,
                'seguindo': False,
                'message': f'Você deixou de seguir {autor.get_display_name()}.'
            })
        else:
            # Não está seguindo → SEGUIR
            AutorSeguido.objects.create(
                seguidor=request.user,
                autor=autor
            )

            # Criar notificação para o autor (Item 3 do ROADMAP)
            try:
                criar_notificacao(
                    usuario_destino=autor,
                    motivo_codigo='NOVO_SEGUIDOR',
                    texto=f'@{request.user.username} está seguindo seu trabalho.',
                    link_destino=f'/@{request.user.username}',
                    usuario_origem=request.user
                )
            except Exception as e:
                # Log do erro, mas não bloqueia o seguimento
                print(f"Erro ao criar notificação de novo seguidor: {e}")

            return JsonResponse({
                'success': True,
                'seguindo': True,
                'message': f'Você agora está seguindo {autor.get_display_name()}! 🔔'
            })

    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Autor não encontrado.'
        }, status=404)
    except Exception as e:
        print(f"Erro ao toggle seguir autor: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Ocorreu um erro. Por favor, tente novamente.'
        }, status=500)
