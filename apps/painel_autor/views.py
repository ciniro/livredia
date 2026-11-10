"""
Views do painel do autor.
"""
from django.views.generic import TemplateView, CreateView, UpdateView, ListView
from django.utils.decorators import method_decorator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.db.models import Count, Q, Sum, Avg, OuterRef, Subquery
from django.db.models.functions import Coalesce

from apps.usuarios.models import User, AutorSeguido
from apps.painel_admin.models import ConviteAutor
from apps.painel_admin.forms import NovoAutorForm
from apps.textos.models import (
    Texto, Tag, Visualizacao, TextoLido, TextoFavorito,
    TextoLeituraPosterior, CartaoBiblioteca
)
from apps.comentarios.models import Comentario
from .decorators import autor_required
from .models import ConfiguracaoAutor
from .forms import ConfiguracaoAutorForm, TextoForm


@method_decorator(autor_required, name='dispatch')
class DashboardAutorView(TemplateView):
    """
    Dashboard do autor com métricas dos seus próprios textos.

    Exibe métricas divididas por categoria:
    - BEM-VINDO: Nome do autor e tempo desde cadastro
    - TEXTOS: Total, Publicados, Rascunhos, Com Selo IA, Com Pseudônimo, Temas mais usados
    - ENGAJAMENTO: Total visualizações, Média, Top 3 textos mais vistos
    - COMENTÁRIOS: Aprovados, Pendentes, Rejeitados
    """
    template_name = 'painel_autor/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # ===== DADOS DO AUTOR =====
        context['autor_nome'] = user.first_name

        # Data de cadastro formatada
        context['data_cadastro'] = user.date_joined.strftime('%d/%m/%Y')

        # Pegar apenas textos do autor logado
        meus_textos = Texto.objects.filter(autor=user)

        # ===== MÉTRICAS DE TEXTOS =====
        context['total_textos'] = meus_textos.count()
        context['textos_publicados'] = meus_textos.filter(status=Texto.Status.PUBLICADO).count()
        context['textos_rascunho'] = meus_textos.filter(status=Texto.Status.RASCUNHO).count()

        # Textos com Selo Livre de IA
        context['textos_com_selo'] = meus_textos.filter(selo_livre_ia=True).count()

        # Textos publicados com pseudônimo (apenas se autor tiver pelo menos 1 texto publicado com pseudônimo)
        textos_com_pseudonimo = meus_textos.filter(
            status=Texto.Status.PUBLICADO,
            display_autoria__in=[Texto.DisplayAutoria.PSEUDONIMO, Texto.DisplayAutoria.AMBOS]
        ).count()

        # Mostrar apenas se > 0
        context['textos_com_pseudonimo'] = textos_com_pseudonimo if textos_com_pseudonimo > 0 else None

        # Temas (tags) mais usados - Top 5
        from django.db.models import Count
        temas_mais_usados = Tag.objects.filter(
            textos__autor=user
        ).annotate(
            quantidade=Count('textos')
        ).order_by('-quantidade')[:5]
        context['temas_mais_usados'] = temas_mais_usados

        # ===== MÉTRICAS DE ENGAJAMENTO =====
        from apps.textos.models import Visualizacao
        from apps.textos.views import formatar_tempo_leitura
        from django.db.models import Sum

        # Exibições totais: contar TODOS os registros de Visualizacao (incluindo reaberturas)
        exibicoes_totais = Visualizacao.objects.filter(texto__autor=user).count()
        context['exibicoes_totais'] = exibicoes_totais

        # Visualizações únicas: contar textos DIFERENTES acessados
        visualizacoes_unicas = Visualizacao.objects.filter(
            texto__autor=user
        ).values('texto').distinct().count()
        context['visualizacoes_unicas'] = visualizacoes_unicas

        # Tempo total de leitura dos textos do autor
        tempo_total_segundos = Visualizacao.objects.filter(
            texto__autor=user,
            tempo_permanencia__isnull=False
        ).aggregate(total=Sum('tempo_permanencia'))['total'] or 0
        context['tempo_total_leitura'] = formatar_tempo_leitura(tempo_total_segundos)

        # Tempo médio de leitura: Tempo total ÷ visualizações únicas
        if visualizacoes_unicas > 0 and tempo_total_segundos > 0:
            tempo_medio_segundos = tempo_total_segundos / visualizacoes_unicas
            context['tempo_medio_leitura'] = formatar_tempo_leitura(int(tempo_medio_segundos))
        else:
            context['tempo_medio_leitura'] = "0s"

        # Top 3 textos mais vistos (anotar com contagem de visualizações)
        context['top_textos_visualizacoes'] = meus_textos.filter(
            status=Texto.Status.PUBLICADO
        ).annotate(
            total_visualizacoes=Count('visualizacoes')
        ).order_by('-total_visualizacoes')[:3]

        # Top 3 textos com mais tempo de leitura
        context['top_textos_tempo'] = meus_textos.filter(
            status=Texto.Status.PUBLICADO
        ).annotate(
            tempo_total=Sum('visualizacoes__tempo_permanencia')
        ).order_by('-tempo_total')[:3]

        # ===== MÉTRICAS DE COMENTÁRIOS =====
        # Comentários aprovados nos textos do autor
        context['comentarios_aprovados'] = Comentario.objects.filter(
            texto__autor=user,
            status=Comentario.Status.APROVADO
        ).count()

        # Comentários pendentes de moderação nos textos do autor
        context['comentarios_pendentes'] = Comentario.objects.filter(
            texto__autor=user,
            status=Comentario.Status.PENDENTE
        ).count()

        # Comentários rejeitados nos textos do autor
        context['comentarios_rejeitados'] = Comentario.objects.filter(
            texto__autor=user,
            status=Comentario.Status.REJEITADO
        ).count()

        return context


@method_decorator(autor_required, name='dispatch')
class ConfiguracoesAutorView(TemplateView):
    """
    Tela de Configurações da Área do Autor.

    Permite ao autor personalizar:
    - Cor de background (12 cores terrosas claras)
    - Emoji de marca d'água (12 ícones populares)

    As configurações são aplicadas automaticamente ao clicar.
    """
    template_name = 'painel_autor/configuracoes.html'

    def get_context_data(self, **kwargs):
        """
        Adiciona informações extras ao contexto do template.
        """
        context = super().get_context_data(**kwargs)

        # Obter ou criar configuração do autor
        config, created = ConfiguracaoAutor.objects.get_or_create(
            autor=self.request.user
        )

        context['config'] = config
        # Cores para light mode e dark mode
        context['cores_light'] = ConfiguracaoAutor.CorBackgroundLight.choices
        context['cores_dark'] = ConfiguracaoAutor.CorBackgroundDark.choices
        context['emojis'] = ConfiguracaoAutor.EmojiMarcaDagua.choices

        # Tema da plataforma (light/dark) - para seção de aparência
        from apps.usuarios.models import ConfiguracaoUsuario
        config_usuario, _ = ConfiguracaoUsuario.objects.get_or_create(
            usuario=self.request.user
        )
        context['tema_plataforma'] = config_usuario.tema_plataforma

        return context


@autor_required
def aplicar_cor(request, cor):
    """
    Aplica uma cor de background (light mode) via HTMX.
    Retorna uma resposta vazia com header HX-Refresh para recarregar a página.
    """
    config, created = ConfiguracaoAutor.objects.get_or_create(
        autor=request.user
    )

    config.cor_background = cor
    config.save()

    # Retornar resposta vazia com refresh
    response = HttpResponse('')
    response['HX-Refresh'] = 'true'
    return response


@autor_required
def remover_cor(request):
    """
    Remove a cor personalizada light mode e volta ao padrão (Pergaminho).
    """
    config, created = ConfiguracaoAutor.objects.get_or_create(
        autor=request.user
    )

    config.cor_background = ConfiguracaoAutor.CorBackgroundLight.PERGAMINHO
    config.save()

    response = HttpResponse('')
    response['HX-Refresh'] = 'true'
    return response


@autor_required
def aplicar_cor_dark(request, cor):
    """
    Aplica uma cor de background (dark mode) via HTMX.
    """
    config, created = ConfiguracaoAutor.objects.get_or_create(
        autor=request.user
    )

    config.cor_background_dark = cor
    config.save()

    response = HttpResponse('')
    response['HX-Refresh'] = 'true'
    return response


@autor_required
def remover_cor_dark(request):
    """
    Remove a cor personalizada dark mode e volta ao padrão (Noite Estrelada).
    """
    config, created = ConfiguracaoAutor.objects.get_or_create(
        autor=request.user
    )

    config.cor_background_dark = ConfiguracaoAutor.CorBackgroundDark.NOITE_ESTRELADA
    config.save()

    response = HttpResponse('')
    response['HX-Refresh'] = 'true'
    return response


@autor_required
def aplicar_emoji(request, emoji):
    """
    Aplica um emoji de marca d'água via HTMX.
    """
    config, created = ConfiguracaoAutor.objects.get_or_create(
        autor=request.user
    )

    config.emoji_marca_dagua = emoji
    config.save()

    response = HttpResponse('')
    response['HX-Refresh'] = 'true'
    return response


@autor_required
def remover_emoji(request):
    """
    Remove o emoji de marca d'água (define como None).
    """
    config, created = ConfiguracaoAutor.objects.get_or_create(
        autor=request.user
    )

    # Não há opção "sem emoji" no modelo, então vamos usar o padrão
    # mas podemos adicionar um campo nullable se preferir
    config.emoji_marca_dagua = None
    config.save()

    response = HttpResponse('')
    response['HX-Refresh'] = 'true'
    return response


# ========================================
# MODERAÇÃO DE COMENTÁRIOS DO AUTOR
# ========================================

@method_decorator(autor_required, name='dispatch')
class ModeracaoAutorListView(ListView):
    """
    Moderação de Comentários do Autor.

    Funciona EXATAMENTE IGUAL à moderação global do painel administrativo,
    com UMA única diferença: exibe apenas comentários de textos escritos
    pelo autor logado (independente de display_autoria).

    Exibe listagem completa de comentários organizados por status:
    - PENDENTES: Comentários aguardando aprovação (autor pode aprovar/rejeitar)
    - APROVADOS: Comentários já aprovados
    - REJEITADOS: Comentários já rejeitados

    Autor tem poder de EXCLUSÃO em qualquer status.

    Filtros (todos trabalham em conjunto):
    - Busca textual no conteúdo do comentário
    - Busca por título da obra
    - Busca por nome ou pseudônimo do autor do comentário
    - Ordenação por data, texto, autor
    """
    model = Comentario
    context_object_name = 'comentarios'
    paginate_by = 100  # Padrão

    def get_template_names(self):
        """
        Retorna template parcial se for requisição HTMX,
        ou template completo se for requisição normal.
        """
        if self.request.headers.get('HX-Request'):
            return ['painel_autor/partials/_tabs_container.html']
        return ['painel_autor/moderacao_autor.html']

    def get_paginate_by(self, queryset):
        """
        Permite ao usuário escolher quantos comentários exibir por página.
        Opções: 30, 50, 100. Padrão: 100.
        """
        per_page = self.request.GET.get('per_page', '100')
        try:
            per_page = int(per_page)
            if per_page in [30, 50, 100]:
                return per_page
        except (ValueError, TypeError):
            pass
        return 100

    def get_queryset(self):
        """
        Retorna comentários (incluindo respostas) APENAS de textos do autor logado,
        filtrados por status (tab) com select_related para otimização de queries.

        DIFERENÇA ÚNICA: Filtro adicional texto__autor=self.request.user

        Filtros (todos trabalham em conjunto):
        - status: PENDENTE (padrão), APROVADO, REJEITADO
        - busca_leitor: Busca por nome do leitor (autor do comentário)
        - busca: Busca textual no conteúdo do comentário
        - busca_titulo: Busca por título da obra

        Ordenação:
        - data (mais recente → mais antigo / mais antigo → mais recente)
        - texto (A-Z / Z-A)
        - autor (A-Z / Z-A)
        """
        # Filtro de status (tab ativa)
        status = self.request.GET.get('status', Comentario.Status.PENDENTE)

        # Validar status
        valid_statuses = [
            Comentario.Status.PENDENTE,
            Comentario.Status.APROVADO,
            Comentario.Status.REJEITADO
        ]

        if status not in valid_statuses:
            status = Comentario.Status.PENDENTE

        # Query base: Comentários APENAS de textos do autor logado
        queryset = Comentario.objects.filter(
            texto__autor=self.request.user,  # <--- FILTRO ÚNICO
            status=status
        ).select_related('autor', 'texto', 'texto__autor', 'pai')

        # Filtro por leitor (autor do comentário)
        busca_leitor = self.request.GET.get('busca_leitor', '').strip()
        if busca_leitor:
            queryset = queryset.filter(
                Q(autor__first_name__icontains=busca_leitor) |
                Q(autor__last_name__icontains=busca_leitor)
            )

        # Filtro de busca textual no conteúdo
        busca = self.request.GET.get('busca', '').strip()
        if busca:
            queryset = queryset.filter(conteudo__icontains=busca)

        # Filtro de busca por título da obra
        busca_titulo = self.request.GET.get('busca_titulo', '').strip()
        if busca_titulo:
            queryset = queryset.filter(texto__titulo__icontains=busca_titulo)

        # Ordenação (padrão: mais recentes primeiro)
        order_by = self.request.GET.get('order_by', '-data_publicacao')

        # Validar campo de ordenação
        valid_orderings = [
            'data_publicacao', '-data_publicacao',
            'texto__titulo', '-texto__titulo',
            'autor__first_name', '-autor__first_name',
        ]

        if order_by in valid_orderings:
            queryset = queryset.order_by(order_by, '-data_publicacao')
        else:
            queryset = queryset.order_by('-data_publicacao')

        return queryset

    def get_context_data(self, **kwargs):
        """
        Adiciona informações extras ao contexto:
        - status_ativa: Status da tab ativa
        - total_pendentes, total_aprovados, total_rejeitados: Contadores por status
        - Parâmetros de filtro para manter estado
        """
        context = super().get_context_data(**kwargs)

        # Status da tab ativa
        context['status_ativa'] = self.request.GET.get('status', Comentario.Status.PENDENTE)

        # Contadores por status (APENAS de textos do autor logado)
        context['total_pendentes'] = Comentario.objects.filter(
            texto__autor=self.request.user,
            status=Comentario.Status.PENDENTE
        ).count()
        context['total_aprovados'] = Comentario.objects.filter(
            texto__autor=self.request.user,
            status=Comentario.Status.APROVADO
        ).count()
        context['total_rejeitados'] = Comentario.objects.filter(
            texto__autor=self.request.user,
            status=Comentario.Status.REJEITADO
        ).count()

        # Parâmetros de filtro/ordenação para manter estado
        context['busca_leitor'] = self.request.GET.get('busca_leitor', '')
        context['busca'] = self.request.GET.get('busca', '')
        context['busca_titulo'] = self.request.GET.get('busca_titulo', '')
        context['order_by'] = self.request.GET.get('order_by', '-data_publicacao')
        context['per_page'] = self.request.GET.get('per_page', '100')

        return context


@autor_required
def aprovar_comentario_autor(request, pk):
    """
    Aprova um comentário PENDENTE em texto do autor logado.

    Apenas comentários PENDENTES podem ser aprovados.
    Comentários já APROVADOS ou REJEITADOS não podem ter decisão revertida.

    Retorna fragment HTML vazio e dispara refresh da página para atualizar contadores.
    """
    comentario = get_object_or_404(
        Comentario,
        pk=pk,
        texto__autor=request.user  # Garantir que é texto do autor
    )

    # Verificar se comentário está pendente
    if comentario.status != Comentario.Status.PENDENTE:
        messages.error(request, 'Apenas comentários pendentes podem ser aprovados.')
        return HttpResponse('', status=400)

    # Aprovar comentário
    comentario.status = Comentario.Status.APROVADO
    comentario.save()

    messages.success(request, 'Comentário aprovado com sucesso.')

    # Retornar HTML vazio com header para refresh da página
    response = HttpResponse('')
    response['HX-Refresh'] = 'true'
    return response


@autor_required
def rejeitar_comentario_autor(request, pk):
    """
    Rejeita um comentário PENDENTE em texto do autor logado.

    Apenas comentários PENDENTES podem ser rejeitados.
    Comentários já APROVADOS ou REJEITADOS não podem ter decisão revertida.

    Retorna fragment HTML vazio e dispara refresh da página para atualizar contadores.
    """
    comentario = get_object_or_404(
        Comentario,
        pk=pk,
        texto__autor=request.user  # Garantir que é texto do autor
    )

    # Verificar se comentário está pendente
    if comentario.status != Comentario.Status.PENDENTE:
        messages.error(request, 'Apenas comentários pendentes podem ser rejeitados.')
        return HttpResponse('', status=400)

    # Rejeitar comentário
    comentario.status = Comentario.Status.REJEITADO
    comentario.save()

    messages.success(request, 'Comentário rejeitado com sucesso.')

    # Retornar HTML vazio com header para refresh da página
    response = HttpResponse('')
    response['HX-Refresh'] = 'true'
    return response


@autor_required
def excluir_comentario_autor(request, pk):
    """
    Exclui um comentário permanentemente de texto do autor logado.

    Autor pode excluir qualquer comentário dos seus textos,
    independente do status (PENDENTE, APROVADO ou REJEITADO).

    Exclusão em cascata: remove comentário + todas as respostas aninhadas.

    Retorna fragment HTML vazio e dispara refresh da página para atualizar contadores.
    """
    comentario = get_object_or_404(
        Comentario,
        pk=pk,
        texto__autor=request.user  # Garantir que é texto do autor
    )

    # Armazenar informações antes de deletar
    autor_nome = "Anônimo" if comentario.publicado_anonimamente else comentario.autor.get_display_name()
    total_respostas = comentario.respostas.count() if not comentario.pai else 0

    # Deletar comentário (cascata: respostas aninhadas)
    comentario.delete()

    # Mensagem de sucesso indicando quantas respostas foram excluídas
    if total_respostas > 0:
        messages.success(
            request,
            f'Comentário de {autor_nome} e suas {total_respostas} resposta(s) foram excluídos permanentemente.'
        )
    else:
        messages.success(
            request,
            f'Comentário de {autor_nome} foi excluído permanentemente.'
        )

    # Retornar HTML vazio com header para refresh da página
    response = HttpResponse('')
    response['HX-Refresh'] = 'true'
    return response


# ========================================
# GESTÃO DE TEXTOS (TELA 21)
# ========================================

@method_decorator(autor_required, name='dispatch')
class MeusTextosListView(ListView):
    """
    Tela 21: Meus Textos (Listagem).

    Exibe todos os textos do autor logado (publicados + rascunhos)
    com estatísticas individuais e ações.

    Funcionalidades:
    - Listagem com cards responsivos (mobile-first)
    - Filtros por status via tabs (Todos, Publicados, Rascunhos)
    - Ordenação (mais recentes, mais antigos, mais visualizados, mais comentados)
    - Paginação configurável (30, 50, 100 textos por página)
    - Ações: Editar, Visualizar, Excluir

    Mobile-first:
    - Cards empilhados verticalmente em mobile
    - Tabela tradicional em desktop
    """
    model = Texto
    context_object_name = 'textos'
    paginate_by = 30  # Padrão

    def get_template_names(self):
        """
        Retorna template parcial se for requisição HTMX,
        ou template completo se for requisição normal.
        """
        if self.request.headers.get('HX-Request'):
            return ['painel_autor/partials/_lista_textos.html']
        return ['painel_autor/meus_textos.html']

    def get_paginate_by(self, queryset):
        """
        Permite ao usuário escolher quantos textos exibir por página.
        Opções: 30, 50, 100. Padrão: 30.
        """
        per_page = self.request.GET.get('per_page', '30')
        try:
            per_page = int(per_page)
            if per_page in [30, 50, 100]:
                return per_page
        except (ValueError, TypeError):
            pass
        return 30

    def get_queryset(self):
        """
        Retorna textos do autor logado, filtrados por status (tab)
        e com anotações de estatísticas (visualizações, comentários).

        Filtros:
        - status: TODOS (padrão), PUBLICADO, RASCUNHO

        Ordenação:
        - mais_recentes (padrão): -data_publicacao, -data_criacao
        - mais_antigos: data_publicacao, data_criacao
        - mais_visualizados: -total_visualizacoes
        - mais_comentados: -total_comentarios
        """
        # Query base: apenas textos do autor logado
        queryset = Texto.objects.filter(autor=self.request.user)

        # Filtro por status (tab ativa)
        status = self.request.GET.get('status', 'TODOS')

        if status == Texto.Status.PUBLICADO:
            queryset = queryset.filter(status=Texto.Status.PUBLICADO)
        elif status == Texto.Status.RASCUNHO:
            queryset = queryset.filter(status=Texto.Status.RASCUNHO)
        # Se 'TODOS', não filtra por status

        # Anotar estatísticas
        queryset = queryset.annotate(
            # Exibições totais: todas as visualizações (incluindo reaberturas)
            exibicoes_totais=Count('visualizacoes'),
            # Total de visualizações (mesmo que exibições totais, mantido para compatibilidade)
            total_visualizacoes=Count('visualizacoes'),
            # Visualizações únicas: usuários únicos que visualizaram (para cada texto individualmente)
            visualizacoes_unicas=Count('visualizacoes__usuario', distinct=True),
            # Total de comentários
            total_comentarios=Count('comentarios', distinct=True),
            # Comentários pendentes
            total_comentarios_pendentes=Count(
                'comentarios',
                filter=Q(comentarios__status=Comentario.Status.PENDENTE),
                distinct=True
            ),
            # Tempo total de leitura
            tempo_total_leitura=Sum('visualizacoes__tempo_permanencia')
        )

        # Ordenação
        order_by = self.request.GET.get('order_by', 'mais_recentes')

        if order_by == 'mais_antigos':
            queryset = queryset.order_by('data_publicacao', 'data_criacao')
        elif order_by == 'mais_visualizados':
            queryset = queryset.order_by('-total_visualizacoes', '-data_publicacao')
        elif order_by == 'mais_comentados':
            queryset = queryset.order_by('-total_comentarios', '-data_publicacao')
        elif order_by == 'maior_tempo_total':
            queryset = queryset.order_by('-tempo_total_leitura', '-data_publicacao')
        elif order_by == 'menor_tempo_total':
            queryset = queryset.order_by('tempo_total_leitura', '-data_publicacao')
        else:  # mais_recentes (padrão)
            queryset = queryset.order_by('-data_publicacao', '-data_criacao')

        return queryset.select_related('autor').prefetch_related('tags')

    def get_context_data(self, **kwargs):
        """
        Adiciona informações extras ao contexto:
        - status_ativa: Status da tab ativa
        - total_todos, total_publicados, total_rascunhos: Contadores por status
        - Parâmetros de filtro para manter estado
        """
        context = super().get_context_data(**kwargs)

        # Status da tab ativa
        context['status_ativa'] = self.request.GET.get('status', 'TODOS')

        # Contadores por status (APENAS textos do autor logado)
        meus_textos = Texto.objects.filter(autor=self.request.user)
        context['total_todos'] = meus_textos.count()
        context['total_publicados'] = meus_textos.filter(status=Texto.Status.PUBLICADO).count()
        context['total_rascunhos'] = meus_textos.filter(status=Texto.Status.RASCUNHO).count()

        # Parâmetros de ordenação e paginação para manter estado
        context['order_by'] = self.request.GET.get('order_by', 'mais_recentes')
        context['per_page'] = self.request.GET.get('per_page', '30')

        return context


@autor_required
def excluir_texto(request, pk):
    """
    Exclui um texto permanentemente do autor logado.

    Segurança:
    - Autor só pode excluir seus próprios textos
    - Exclusão em cascata: remove texto + comentários + visualizações

    Retorna fragment HTML vazio e dispara refresh da página.
    """
    texto = get_object_or_404(
        Texto,
        pk=pk,
        autor=request.user  # Garantir que é texto do autor
    )

    # Armazenar informações antes de deletar
    titulo = texto.titulo
    total_comentarios = texto.comentarios.count()
    total_visualizacoes = texto.visualizacoes.count()

    # Deletar texto (cascata: comentários + visualizações)
    texto.delete()

    # Mensagem de sucesso com estatísticas
    messages.success(
        request,
        f'Texto "{titulo}" foi excluído permanentemente. '
        f'({total_comentarios} comentário(s) e {total_visualizacoes} visualização(ões) também foram removidos)'
    )

    # Retornar HTML vazio com header para refresh da página
    response = HttpResponse('')
    response['HX-Refresh'] = 'true'
    return response


@autor_required
def toggle_status_texto(request, pk):
    """
    Alterna o status do texto entre PUBLICADO e RASCUNHO.

    PUBLICADO → RASCUNHO: Remove data de publicação
    RASCUNHO → PUBLICADO: Define data de publicação como agora

    Segurança:
    - Autor só pode alterar status dos seus próprios textos

    Retorna fragment HTML vazio e dispara refresh da página.
    """
    texto = get_object_or_404(
        Texto,
        pk=pk,
        autor=request.user  # Garantir que é texto do autor
    )

    # ITEM 3 DO ROADMAP - Armazenar status anterior para verificar se deve notificar
    status_anterior = texto.status

    # Alternar status
    if texto.status == Texto.Status.PUBLICADO:
        # De PUBLICADO para RASCUNHO
        texto.status = Texto.Status.RASCUNHO
        texto.data_publicacao = None
        messages.success(request, f'Texto "{texto.titulo}" despublicado com sucesso.')
    else:
        # De RASCUNHO para PUBLICADO
        texto.status = Texto.Status.PUBLICADO
        if not texto.data_publicacao:
            texto.data_publicacao = timezone.now()
        messages.success(request, f'Texto "{texto.titulo}" publicado com sucesso.')

    texto.save()

    # ITEM 3 DO ROADMAP - Notificações de publicação por e-mail
    # Notificar seguidores APENAS quando muda de RASCUNHO para PUBLICADO
    if status_anterior == Texto.Status.RASCUNHO and texto.status == Texto.Status.PUBLICADO:
        from apps.core.utils import notificar_seguidores_novo_texto
        try:
            notificar_seguidores_novo_texto(texto)
        except Exception as e:
            # Não interromper publicação se notificação falhar
            print(f"Erro ao notificar seguidores: {str(e)}")

    # Retornar HTML vazio com header para refresh da página
    response = HttpResponse('')
    response['HX-Refresh'] = 'true'
    return response


# ============================================================================
# GUIA DO EDITOR - Página de ajuda do editor de texto
# ============================================================================

class GuiaEditorView(TemplateView):
    """
    Página de ajuda com documentação das funcionalidades do editor de texto.

    Não requer autenticação pois é apenas documentação.
    Abre em nova aba quando clica no botão "Ajuda" do editor.
    """
    template_name = 'painel_autor/guia_editor.html'


# ============================================================================
# EDITOR DE TEXTO - Criar/Editar Textos
# ============================================================================

@method_decorator(autor_required, name='dispatch')
class NovoTextoView(CreateView):
    """
    View para criar novo texto.

    Características:
    - Formulário com Quill.js para conteúdo
    - Seleção de tags (grid clicável + criar nova)
    - Auto-save a cada 60 segundos
    - Gera slug automaticamente
    - Suporta rascunho e publicação

    Defaults:
    - selo_livre_ia = True
    - permite_comentarios = True
    - moderacao_automatica = True
    - permite_comentarios_anonimos = False
    """
    model = Texto
    form_class = TextoForm
    template_name = 'painel_autor/editor_texto.html'

    def get_form_kwargs(self):
        """
        Passar autor ao formulário.
        """
        kwargs = super().get_form_kwargs()
        kwargs['autor'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        """
        Adicionar dados extras ao contexto:
        - todas_tags: Lista de todas as tags cadastradas
        - tags_mais_usadas: 15 tags mais usadas pelo autor com contador
        - tags_em_uso: Set de IDs das tags que estão sendo usadas por algum texto
        - titulo_pagina: "Novo Texto"
        - acao: "criar"
        """
        context = super().get_context_data(**kwargs)

        # Buscar todas as tags ordenadas por nome com contador de uso global
        from django.db.models import Count
        context['todas_tags'] = Tag.objects.annotate(
            total_usos=Count('textos', distinct=True)
        ).order_by('nome')

        # Calcular estatísticas: TODOS os tags já usados pelo autor
        # Contabilizar textos publicados E rascunhos
        tags_com_contador = Tag.objects.filter(
            textos__autor=self.request.user
        ).annotate(
            contador=Count('textos')
        ).order_by('-contador', 'nome')

        # Pegar TODOS os temas usados pelo autor (não apenas top 15)
        context['tags_mais_usadas'] = list(tags_com_contador)
        context['total_tags'] = Tag.objects.count()

        # Identificar quais tags estão em uso (por qualquer texto de qualquer autor)
        tags_em_uso_ids = Texto.objects.filter(
            tags__isnull=False
        ).values_list('tags__id', flat=True).distinct()
        context['tags_em_uso'] = set(tags_em_uso_ids)

        context['titulo_pagina'] = 'Novo Texto'
        context['acao'] = 'criar'
        return context

    def form_valid(self, form):
        """
        Processar formulário válido.

        Lógica:
        - Verificar se já existe um texto criado pelo auto-save
        - Se sim, atualizar esse texto (evitar duplicação)
        - Se não, criar novo texto
        - Se clicou em "Salvar Rascunho": status = RASCUNHO
        - Se clicou em "Publicar": status = PUBLICADO + data_publicacao = now
        """

        # Verificar qual botão foi clicado
        acao = self.request.POST.get('acao', 'rascunho')

        # IMPORTANTE: Verificar se já existe um texto criado pelo auto-save
        texto_id = self.request.POST.get('texto_id')

        if texto_id:
            # Atualizar texto existente (criado pelo auto-save ou pré-visualização)
            try:
                texto = Texto.objects.get(pk=texto_id, autor=self.request.user)
                # Atualizar form.instance para que o form use o texto existente
                form.instance = texto
                # Agora salvar usando o form (atualiza todos os campos)
                texto = form.save(commit=False)
                # Autor já está definido, mas garantir
                texto.autor = self.request.user
            except Texto.DoesNotExist:
                # Se não encontrou, criar novo
                texto = form.save(commit=False)
                texto.autor = self.request.user
        else:
            # Criar novo texto
            texto = form.save(commit=False)
            texto.autor = self.request.user

        if acao == 'publicar':
            # Publicar imediatamente
            texto.status = Texto.Status.PUBLICADO
            texto.data_publicacao = timezone.now()
            mensagem = f'Parabéns! Seu texto "{texto.titulo}" foi publicado com sucesso!'
        else:
            # Salvar como rascunho
            texto.status = Texto.Status.RASCUNHO
            texto.data_publicacao = None
            mensagem = f'Texto "{texto.titulo}" salvo como rascunho.'

        texto.save()

        # Atualizar tags (ManyToMany)
        texto.tags.set(form.cleaned_data['tags'])

        # ITEM 3 DO ROADMAP - Notificações de publicação por e-mail
        # Notificar seguidores APENAS se autor escolheu "Publicar avisando meus seguidores"
        notificar_seguidores = self.request.POST.get('notificar_seguidores', 'false') == 'true'
        if acao == 'publicar' and notificar_seguidores:
            from apps.core.utils import notificar_seguidores_novo_texto
            try:
                notificar_seguidores_novo_texto(texto)
            except Exception as e:
                # Não interromper publicação se notificação falhar
                print(f"Erro ao notificar seguidores: {str(e)}")

        # Verificar se é requisição AJAX (preview ou salvar rascunho via AJAX)
        is_ajax = self.request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        is_preview = self.request.POST.get('preview') == 'true'

        if is_ajax:
            if is_preview:
                # Retornar JSON com URL do texto para abrir em nova aba
                preview_url = reverse('textos:leitura_texto', kwargs={'pk': texto.pk})
                return JsonResponse({
                    'success': True,
                    'texto_id': texto.pk,
                    'url': preview_url,
                    'message': mensagem
                })
            elif acao == 'publicar':
                # Retornar JSON para abrir em nova aba via JavaScript
                return JsonResponse({
                    'success': True,
                    'texto_id': texto.pk,
                    'open_in_new_tab': True,
                    'url': reverse('textos:leitura_texto', kwargs={'pk': texto.pk}),
                    'redirect_url': reverse('painel_autor:meus_textos'),
                    'message': mensagem
                })
            else:
                # Salvar rascunho via AJAX - apenas retornar sucesso
                return JsonResponse({
                    'success': True,
                    'texto_id': texto.pk,
                    'message': mensagem
                })

        # Requisição normal (não AJAX) - redirecionar
        messages.success(self.request, mensagem)

        if acao == 'publicar':
            self.success_url = reverse('textos:leitura_texto', kwargs={'pk': texto.pk})
        else:
            # Redirecionar para página de edição (mantém dados preenchidos)
            self.success_url = reverse('painel_autor:editar_texto', kwargs={'pk': texto.pk})

        return super().form_valid(form)


@method_decorator(autor_required, name='dispatch')
class EditarTextoView(UpdateView):
    """
    View para editar texto existente.

    Características:
    - Formulário idêntico ao de criação
    - Campos pré-preenchidos
    - IMPORTANTE: Editar texto PUBLICADO volta para RASCUNHO
    - Autor só pode editar seus próprios textos
    """
    model = Texto
    form_class = TextoForm
    template_name = 'painel_autor/editor_texto.html'

    def get_queryset(self):
        """
        Filtrar apenas textos do autor logado.

        Segurança:
        - Autor só pode editar seus próprios textos
        """
        return Texto.objects.filter(autor=self.request.user)

    def get_form_kwargs(self):
        """
        Passar autor ao formulário.
        """
        kwargs = super().get_form_kwargs()
        kwargs['autor'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        """
        Adicionar dados extras ao contexto:
        - todas_tags: Lista de todas as tags cadastradas
        - tags_mais_usadas: 15 tags mais usadas pelo autor com contador
        - tags_selecionadas: IDs das tags já vinculadas ao texto
        - tags_em_uso: Set de IDs das tags que estão sendo usadas por algum texto
        - titulo_pagina: "Editar: [nome do texto]"
        - acao: "editar"
        - status_anterior: Status do texto antes de editar
        """
        context = super().get_context_data(**kwargs)

        # Buscar todas as tags ordenadas por nome com contador de uso global
        from django.db.models import Count
        context['todas_tags'] = Tag.objects.annotate(
            total_usos=Count('textos', distinct=True)
        ).order_by('nome')

        # Calcular estatísticas: TODOS os tags já usados pelo autor
        # Contabilizar textos publicados E rascunhos
        tags_com_contador = Tag.objects.filter(
            textos__autor=self.request.user
        ).annotate(
            contador=Count('textos')
        ).order_by('-contador', 'nome')

        # Pegar TODOS os temas usados pelo autor (não apenas top 15)
        context['tags_mais_usadas'] = list(tags_com_contador)
        context['total_tags'] = Tag.objects.count()

        # Identificar quais tags estão em uso (por qualquer texto de qualquer autor)
        tags_em_uso_ids = Texto.objects.filter(
            tags__isnull=False
        ).values_list('tags__id', flat=True).distinct()
        context['tags_em_uso'] = set(tags_em_uso_ids)

        context['tags_selecionadas'] = list(self.object.tags.values_list('id', flat=True))
        context['titulo_pagina'] = f'Editar: {self.object.titulo}'
        context['acao'] = 'editar'
        context['status_anterior'] = self.object.status
        return context

    def form_valid(self, form):
        """
        Processar formulário válido.

        IMPORTANTE: Editar texto PUBLICADO volta para RASCUNHO.

        Lógica:
        - Se clicou em "Salvar Rascunho": status = RASCUNHO
        - Se clicou em "Publicar": status = PUBLICADO + data_publicacao = now
        """
        # Verificar qual botão foi clicado
        acao = self.request.POST.get('acao', 'rascunho')

        # Salvar texto (sem commit para ajustar antes)
        texto = form.save(commit=False)

        # ITEM 3 DO ROADMAP - Armazenar status anterior para verificar se deve notificar
        status_anterior = self.object.status

        # REGRA: Editar texto publicado volta para rascunho
        # Só publica se clicar explicitamente em "Publicar"
        if acao == 'publicar':
            texto.status = Texto.Status.PUBLICADO
            # Se já foi publicado antes, manter data original
            # Se nunca foi publicado, definir data agora
            if not texto.data_publicacao:
                texto.data_publicacao = timezone.now()
            mensagem = f'Texto "{texto.titulo}" publicado com sucesso!'
        else:
            # Salvar como rascunho (mesmo que estava publicado)
            texto.status = Texto.Status.RASCUNHO
            mensagem = f'Texto "{texto.titulo}" salvo como rascunho.'

        texto.save()
        form.save_m2m()  # Salvar tags (ManyToMany)

        # ITEM 3 DO ROADMAP - Notificações de publicação por e-mail
        # Notificar seguidores APENAS se:
        # 1. Texto estava em RASCUNHO e passou para PUBLICADO
        # 2. Autor escolheu "Publicar avisando meus seguidores"
        notificar_seguidores = self.request.POST.get('notificar_seguidores', 'false') == 'true'
        if acao == 'publicar' and status_anterior == Texto.Status.RASCUNHO and notificar_seguidores:
            from apps.core.utils import notificar_seguidores_novo_texto
            try:
                notificar_seguidores_novo_texto(texto)
            except Exception as e:
                # Não interromper publicação se notificação falhar
                print(f"Erro ao notificar seguidores: {str(e)}")

        # Verificar se é requisição AJAX (preview ou salvar rascunho via AJAX)
        is_ajax = self.request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        is_preview = self.request.POST.get('preview') == 'true'

        if is_ajax:
            if is_preview:
                # Retornar JSON com URL do texto para abrir em nova aba
                preview_url = reverse('textos:leitura_texto', kwargs={'pk': texto.pk})
                return JsonResponse({
                    'success': True,
                    'texto_id': texto.pk,
                    'url': preview_url,
                    'message': mensagem
                })
            elif acao == 'publicar':
                # Retornar JSON para abrir em nova aba via JavaScript
                return JsonResponse({
                    'success': True,
                    'texto_id': texto.pk,
                    'open_in_new_tab': True,
                    'url': reverse('textos:leitura_texto', kwargs={'pk': texto.pk}),
                    'redirect_url': reverse('painel_autor:meus_textos'),
                    'message': mensagem
                })
            else:
                # Salvar rascunho via AJAX - apenas retornar sucesso
                return JsonResponse({
                    'success': True,
                    'texto_id': texto.pk,
                    'message': mensagem
                })

        # Requisição normal (não AJAX) - redirecionar
        messages.success(self.request, mensagem)

        if acao == 'publicar':
            self.success_url = reverse('textos:leitura_texto', kwargs={'pk': texto.pk})
        else:
            # Redirecionar para página de edição (mantém dados preenchidos)
            self.success_url = reverse('painel_autor:editar_texto', kwargs={'pk': texto.pk})

        return super().form_valid(form)


@autor_required
def auto_save_texto(request):
    """
    Auto-save de rascunho via AJAX (a cada 60 segundos).

    POST params:
    - texto_id (opcional): ID do texto sendo editado
    - titulo: Título do texto
    - subtitulo: Subtítulo (opcional)
    - conteudo: HTML do Quill.js
    - tags: IDs das tags selecionadas (lista)

    Retorna JSON:
    - success: True/False
    - texto_id: ID do texto salvo
    - mensagem: Mensagem de feedback
    - timestamp: Timestamp do salvamento
    """
    import json

    if request.method != 'POST':
        return JsonResponse({'success': False, 'mensagem': 'Método não permitido'}, status=405)

    try:
        # Obter dados do POST
        texto_id = request.POST.get('texto_id')
        titulo = request.POST.get('titulo', '').strip()
        subtitulo = request.POST.get('subtitulo', '').strip()
        conteudo = request.POST.get('conteudo', '').strip()
        tags_ids = request.POST.getlist('tags[]')

        # Validações básicas
        if not titulo or len(titulo) < 3:
            return JsonResponse({
                'success': False,
                'mensagem': 'Título deve ter no mínimo 3 caracteres'
            }, status=400)

        # Se texto_id existe, editar. Senão, criar novo
        if texto_id:
            # Editar texto existente
            texto = get_object_or_404(Texto, pk=texto_id, autor=request.user)
            texto.titulo = titulo
            texto.subtitulo = subtitulo if subtitulo else None
            texto.conteudo = conteudo
        else:
            # Criar novo texto (rascunho)
            form = TextoForm()
            texto = Texto(
                autor=request.user,
                titulo=titulo,
                subtitulo=subtitulo if subtitulo else None,
                conteudo=conteudo,
                slug=form.gerar_slug_unico(titulo),
                status=Texto.Status.RASCUNHO,
                # Defaults
                selo_livre_ia=True,
                permite_comentarios=True,
                moderacao_automatica=True,
                permite_comentarios_anonimos=False,
                display_autoria=Texto.DisplayAutoria.REAL
            )

        texto.save()

        # Atualizar tags
        if tags_ids:
            texto.tags.set(Tag.objects.filter(id__in=tags_ids))

        # Retornar sucesso
        return JsonResponse({
            'success': True,
            'texto_id': texto.id,
            'mensagem': 'Rascunho salvo automaticamente',
            'timestamp': timezone.now().strftime('%H:%M:%S')
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'mensagem': f'Erro ao salvar: {str(e)}'
        }, status=500)


@autor_required
def criar_tag_ajax(request):
    """
    Criar nova tag via AJAX.

    POST params:
    - nome: Nome da tag

    Retorna JSON:
    - success: True/False
    - tag_id: ID da tag criada
    - tag_nome: Nome da tag
    - tag_slug: Slug da tag
    - mensagem: Mensagem de feedback
    """
    import json

    if request.method != 'POST':
        return JsonResponse({'success': False, 'mensagem': 'Método não permitido'}, status=405)

    try:
        nome = request.POST.get('nome', '').strip()

        # Validações
        if not nome or len(nome) < 2:
            return JsonResponse({
                'success': False,
                'mensagem': 'Nome do tema deve ter no mínimo 2 caracteres'
            }, status=400)

        # Formatar nome: primeira letra de cada palavra em maiúscula (Title Case)
        # Exemplo: "carnaval festivo" → "Carnaval Festivo"
        nome = nome.title()

        # Verificar se já existe
        tag_existente = Tag.objects.filter(nome__iexact=nome).first()
        if tag_existente:
            return JsonResponse({
                'success': True,
                'tag_id': tag_existente.id,
                'tag_nome': tag_existente.nome,
                'tag_slug': tag_existente.slug,
                'mensagem': 'Tema já existe',
                'ja_existia': True
            })

        # Criar nova tag com nome formatado
        tag = Tag.objects.create(nome=nome)

        return JsonResponse({
            'success': True,
            'tag_id': tag.id,
            'tag_nome': tag.nome,
            'tag_slug': tag.slug,
            'total_usos': 0,  # Novo tema nunca foi usado
            'mensagem': 'Tema criado com sucesso',
            'ja_existia': False
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'mensagem': f'Erro ao criar tema: {str(e)}'
        }, status=500)


@autor_required
def editar_tag_ajax(request):
    """
    Editar uma tag via AJAX (somente se não estiver em uso).

    POST params:
    - tag_id: ID da tag a ser editada
    - novo_nome: Novo nome da tag

    Retorna JSON:
    - success: True/False
    - tag_id: ID da tag editada
    - tag_nome: Novo nome da tag
    - mensagem: Mensagem de feedback
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'mensagem': 'Método não permitido'}, status=405)

    try:
        tag_id = request.POST.get('tag_id', '').strip()
        novo_nome = request.POST.get('novo_nome', '').strip()

        # Validações básicas
        if not tag_id or not novo_nome:
            return JsonResponse({
                'success': False,
                'mensagem': 'ID da tag e novo nome são obrigatórios'
            }, status=400)

        if len(novo_nome) < 2:
            return JsonResponse({
                'success': False,
                'mensagem': 'Nome do tema deve ter no mínimo 2 caracteres'
            }, status=400)

        # Formatar nome: primeira letra de cada palavra em maiúscula (Title Case)
        # Exemplo: "carnaval festivo" → "Carnaval Festivo"
        novo_nome = novo_nome.title()

        # Buscar a tag
        tag = get_object_or_404(Tag, id=tag_id)

        # Verificar se a tag está em uso por algum texto
        textos_usando = Texto.objects.filter(tags=tag).count()
        if textos_usando > 0:
            return JsonResponse({
                'success': False,
                'mensagem': f'Não é possível editar este tema porque ele está sendo usado por {textos_usando} texto(s)',
                'em_uso': True,
                'total_textos': textos_usando
            }, status=403)

        # Verificar se já existe outro tema com esse nome (apenas se o nome mudou)
        if tag.nome.lower() != novo_nome.lower():
            tag_duplicada = Tag.objects.filter(nome__iexact=novo_nome).exclude(id=tag_id).first()
            if tag_duplicada:
                return JsonResponse({
                    'success': False,
                    'mensagem': 'Já existe outro tema com este nome',
                    'duplicado': True
                }, status=400)

        # Atualizar o nome formatado
        tag.nome = novo_nome
        tag.save()

        return JsonResponse({
            'success': True,
            'tag_id': tag.id,
            'tag_nome': tag.nome,
            'tag_slug': tag.slug,
            'mensagem': 'Tema editado com sucesso'
        })

    except Tag.DoesNotExist:
        return JsonResponse({
            'success': False,
            'mensagem': 'Tema não encontrado'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'mensagem': f'Erro ao editar tema: {str(e)}'
        }, status=500)


@autor_required
def excluir_tag_ajax(request):
    """
    Excluir uma tag via AJAX (somente se não estiver em uso).

    POST params:
    - tag_id: ID da tag a ser excluída

    Retorna JSON:
    - success: True/False
    - mensagem: Mensagem de feedback
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'mensagem': 'Método não permitido'}, status=405)

    try:
        tag_id = request.POST.get('tag_id', '').strip()

        # Validação básica
        if not tag_id:
            return JsonResponse({
                'success': False,
                'mensagem': 'ID da tag é obrigatório'
            }, status=400)

        # Buscar a tag
        tag = get_object_or_404(Tag, id=tag_id)

        # Verificar se a tag está em uso por algum texto
        textos_usando = Texto.objects.filter(tags=tag).count()
        if textos_usando > 0:
            return JsonResponse({
                'success': False,
                'mensagem': f'Não é possível excluir este tema porque ele está sendo usado por {textos_usando} texto(s)',
                'em_uso': True,
                'total_textos': textos_usando
            }, status=403)

        # Salvar nome antes de excluir
        tag_nome = tag.nome

        # Excluir a tag
        tag.delete()

        return JsonResponse({
            'success': True,
            'tag_id': tag_id,
            'tag_nome': tag_nome,
            'mensagem': 'Tema excluído com sucesso'
        })

    except Tag.DoesNotExist:
        return JsonResponse({
            'success': False,
            'mensagem': 'Tema não encontrado'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'mensagem': f'Erro ao excluir tema: {str(e)}'
        }, status=500)


# ====================================================================
# SISTEMA DE SELOS - MEUS SEGUIDORES (Item 1 do ROADMAP)
# ====================================================================

def calcular_estatisticas_seguidor(seguidor, autor):
    """
    Calcula todas as estatísticas de engajamento de um seguidor com os textos de um autor.

    ETAPA 3 - Item 1 do ROADMAP (Sistema de Selos de Leitor Especial)

    Args:
        seguidor: User object do seguidor
        autor: User object do autor

    Returns:
        dict: Dicionário com todas as métricas calculadas:
            - visualizacoes_autor: Total de visualizações nos textos do autor
            - visualizacoes_total: Total de visualizações na plataforma
            - percentual_visualizacoes: Percentual (0-100)
            - tempo_leitura_autor: Tempo em segundos nos textos do autor
            - tempo_leitura_total: Tempo em segundos na plataforma
            - percentual_tempo: Percentual (0-100)
            - tempo_leitura_autor_formatado: String "Xh Ymin"
            - tempo_leitura_total_formatado: String "Xh Ymin"
            - comentarios: Quantidade de comentários nos textos do autor
            - textos_lidos: Quantidade de textos lidos do autor
            - textos_favoritos: Quantidade de textos favoritos do autor
            - textos_lista_leitura: Quantidade de textos do autor na lista de leitura
            - cartoes_assinados: Quantidade de cartões assinados nos textos do autor
    """

    # ===== VISUALIZAÇÕES =====
    # Total de visualizações nos textos do autor
    visualizacoes_autor = Visualizacao.objects.filter(
        usuario=seguidor,
        texto__autor=autor
    ).count()

    # Total de visualizações na plataforma inteira
    visualizacoes_total = Visualizacao.objects.filter(
        usuario=seguidor
    ).count()

    # Percentual de visualizações
    percentual_visualizacoes = (
        (visualizacoes_autor / visualizacoes_total * 100)
        if visualizacoes_total > 0 else 0
    )

    # ===== TEMPO DE LEITURA =====
    # Tempo total de leitura nos textos do autor (em segundos)
    tempo_autor_aggregate = Visualizacao.objects.filter(
        usuario=seguidor,
        texto__autor=autor
    ).aggregate(total=Sum('tempo_permanencia'))
    tempo_leitura_autor = tempo_autor_aggregate['total'] or 0

    # Tempo total de leitura na plataforma (em segundos)
    tempo_total_aggregate = Visualizacao.objects.filter(
        usuario=seguidor
    ).aggregate(total=Sum('tempo_permanencia'))
    tempo_leitura_total = tempo_total_aggregate['total'] or 0

    # Percentual de tempo de leitura
    percentual_tempo = (
        (tempo_leitura_autor / tempo_leitura_total * 100)
        if tempo_leitura_total > 0 else 0
    )

    # Formatar tempo para "Xh Ymin"
    def formatar_tempo(segundos):
        if segundos == 0:
            return "0min"
        horas = segundos // 3600
        minutos = (segundos % 3600) // 60
        if horas > 0:
            return f"{horas}h {minutos}min"
        return f"{minutos}min"

    tempo_leitura_autor_formatado = formatar_tempo(tempo_leitura_autor)
    tempo_leitura_total_formatado = formatar_tempo(tempo_leitura_total)

    # ===== COMENTÁRIOS =====
    comentarios = Comentario.objects.filter(
        autor=seguidor,
        texto__autor=autor
    ).count()

    # ===== TEXTOS LIDOS =====
    textos_lidos = TextoLido.objects.filter(
        usuario=seguidor,
        texto__autor=autor
    ).count()

    # ===== TEXTOS FAVORITOS =====
    textos_favoritos = TextoFavorito.objects.filter(
        usuario=seguidor,
        texto__autor=autor
    ).count()

    # ===== TEXTOS NA LISTA DE LEITURA =====
    textos_lista_leitura = TextoLeituraPosterior.objects.filter(
        usuario=seguidor,
        texto__autor=autor
    ).count()

    # ===== CARTÕES ASSINADOS =====
    cartoes_assinados = CartaoBiblioteca.objects.filter(
        usuario=seguidor,
        texto__autor=autor
    ).count()

    return {
        'visualizacoes_autor': visualizacoes_autor,
        'visualizacoes_total': visualizacoes_total,
        'percentual_visualizacoes': round(percentual_visualizacoes, 1),
        'tempo_leitura_autor': tempo_leitura_autor,
        'tempo_leitura_total': tempo_leitura_total,
        'percentual_tempo': round(percentual_tempo, 1),
        'tempo_leitura_autor_formatado': tempo_leitura_autor_formatado,
        'tempo_leitura_total_formatado': tempo_leitura_total_formatado,
        'comentarios': comentarios,
        'textos_lidos': textos_lidos,
        'textos_favoritos': textos_favoritos,
        'textos_lista_leitura': textos_lista_leitura,
        'cartoes_assinados': cartoes_assinados,
    }


@method_decorator(autor_required, name='dispatch')
class MeusSeguidoresView(ListView):
    """
    Tela "Meus Seguidores" do painel do autor.

    ETAPAS 2-3 - Item 1 do ROADMAP (Sistema de Selos de Leitor Especial):
    Exibe lista paginada de seguidores com estatísticas completas de engajamento.

    Cada card exibe:
    - Informações básicas: foto, nome, username, localização, sexo, datas
    - Estatísticas de visualização: total no autor, total na plataforma, percentual
    - Estatísticas de tempo: tempo no autor, tempo total, percentual
    - Métricas de engajamento: comentários, textos lidos, favoritos, lista, cartões

    Paginação: 12 seguidores por página
    Ordenação padrão: Mais recentes primeiro (-data_seguimento)
    """
    model = AutorSeguido
    template_name = 'painel_autor/meus_seguidores.html'
    context_object_name = 'seguidores'
    paginate_by = 12  # 12 seguidores por página

    def get_queryset(self):
        """
        Retorna seguidores do autor logado com suporte a filtros e ordenação.

        ETAPA 4: Filtros e Ordenação

        Filtros:
        - busca: Nome ou username do seguidor
        - apenas_especiais: Checkbox para filtrar apenas leitores especiais

        Ordenação (order_by):
        - antigos (padrão): data_seguimento (mais antigos primeiro)
        - visualizacoes: -total_visualizacoes
        - tempo_leitura: -total_tempo_leitura
        - lidos: -total_lidos
        - favoritos: -total_favoritos
        - cartoes: -total_cartoes

        Usa select_related e annotate para otimizar queries.
        """
        # Query base: seguidores do autor logado
        queryset = AutorSeguido.objects.filter(
            autor=self.request.user
        ).select_related('seguidor')

        # ETAPA 4: Filtro de busca (nome ou username)
        busca = self.request.GET.get('busca', '').strip()
        if busca:
            queryset = queryset.filter(
                Q(seguidor__first_name__icontains=busca) |
                Q(seguidor__last_name__icontains=busca) |
                Q(seguidor__username__icontains=busca)
            )

        # ETAPA 4: Filtro "apenas leitores especiais"
        apenas_especiais = self.request.GET.get('apenas_especiais', '')
        if apenas_especiais == 'on':
            queryset = queryset.filter(is_leitor_especial=True)

        # ETAPA 4: Annotate com métricas para ordenação
        # IMPORTANTE: Usar subqueries para evitar duplicação causada por múltiplos JOINs
        # (Problema: Count + Sum juntos criam produto cartesiano que multiplica valores)

        # Subquery para contar visualizações
        visualizacoes_subquery = Visualizacao.objects.filter(
            usuario=OuterRef('seguidor'),
            texto__autor=self.request.user
        ).values('usuario').annotate(count=Count('id')).values('count')

        # Subquery para somar tempo de leitura
        tempo_subquery = Visualizacao.objects.filter(
            usuario=OuterRef('seguidor'),
            texto__autor=self.request.user
        ).values('usuario').annotate(total=Sum('tempo_permanencia')).values('total')

        # Subquery para contar textos lidos
        lidos_subquery = TextoLido.objects.filter(
            usuario=OuterRef('seguidor'),
            texto__autor=self.request.user
        ).values('usuario').annotate(count=Count('id')).values('count')

        # Subquery para contar favoritos
        favoritos_subquery = TextoFavorito.objects.filter(
            usuario=OuterRef('seguidor'),
            texto__autor=self.request.user
        ).values('usuario').annotate(count=Count('id')).values('count')

        # Subquery para contar cartões assinados
        cartoes_subquery = CartaoBiblioteca.objects.filter(
            usuario=OuterRef('seguidor'),
            texto__autor=self.request.user
        ).values('usuario').annotate(count=Count('id')).values('count')

        # Subquery para contar comentários
        comentarios_subquery = Comentario.objects.filter(
            autor=OuterRef('seguidor'),
            texto__autor=self.request.user,
            status=Comentario.Status.APROVADO
        ).values('autor').annotate(count=Count('id')).values('count')

        # Aplicar subqueries como annotate
        queryset = queryset.annotate(
            total_visualizacoes=Coalesce(Subquery(visualizacoes_subquery), 0),
            total_tempo_leitura=Coalesce(Subquery(tempo_subquery), 0),
            total_lidos=Coalesce(Subquery(lidos_subquery), 0),
            total_favoritos=Coalesce(Subquery(favoritos_subquery), 0),
            total_cartoes=Coalesce(Subquery(cartoes_subquery), 0),
            total_comentarios=Coalesce(Subquery(comentarios_subquery), 0)
        )

        # ETAPA 4: Ordenação
        order_by = self.request.GET.get('order_by', 'antigos')

        order_mapping = {
            'antigos': 'data_seguimento',  # Mais antigos primeiro (crescente)
            'visualizacoes': '-total_visualizacoes',
            'tempo_leitura': '-total_tempo_leitura',
            'comentarios': '-total_comentarios',
            'lidos': '-total_lidos',
            'favoritos': '-total_favoritos',
            'cartoes': '-total_cartoes',
        }

        order_field = order_mapping.get(order_by, 'data_seguimento')
        queryset = queryset.order_by(order_field, 'data_seguimento')  # Desempate por data (antigos)

        return queryset

    def get_context_data(self, **kwargs):
        """
        Adiciona informações extras ao contexto do template.

        ETAPA 3: Calcula estatísticas de engajamento para cada seguidor na página atual.
        As estatísticas são adicionadas como atributo 'estatisticas' em cada objeto AutorSeguido.

        ETAPA 4: Adiciona parâmetros de filtro/ordenação ao contexto para manter estado.
        """
        context = super().get_context_data(**kwargs)

        # Total de seguidores do autor
        context['total_seguidores'] = self.get_queryset().count()

        # ETAPA 4: Parâmetros de filtro/ordenação para manter estado no template
        context['order_by'] = self.request.GET.get('order_by', 'antigos')
        context['busca'] = self.request.GET.get('busca', '')
        context['apenas_especiais'] = self.request.GET.get('apenas_especiais', '')

        # ETAPA 3: Calcular estatísticas para cada seguidor na página atual
        autor = self.request.user
        seguidores_pagina = context['seguidores']  # QuerySet da página atual (paginado)

        for autor_seguido in seguidores_pagina:
            # Adiciona estatísticas como atributo no objeto AutorSeguido
            autor_seguido.estatisticas = calcular_estatisticas_seguidor(
                seguidor=autor_seguido.seguidor,
                autor=autor
            )

        return context


# =============================================================================
# ETAPA 5: MARCAR/DESMARCAR LEITOR ESPECIAL
# =============================================================================

@autor_required
def marcar_leitor_especial(request, seguidor_id):
    """
    ETAPA 5 - Sistema de Selos de Leitor Especial.

    Endpoint para marcar um seguidor como "leitor especial".

    Ações:
    1. Busca o relacionamento AutorSeguido
    2. Verifica se o autor logado é o dono do relacionamento
    3. Marca is_leitor_especial = True
    4. Cria notificação para o seguidor usando criar_notificacao()
    5. Retorna HTML atualizado do card para HTMX

    Args:
        request: HttpRequest
        seguidor_id (int): ID do relacionamento AutorSeguido

    Returns:
        HttpResponse com HTML do card atualizado
    """
    from apps.core.utils import criar_notificacao
    from django.template.loader import render_to_string

    if request.method != 'POST':
        return HttpResponse('Método não permitido', status=405)

    try:
        # Buscar relacionamento e verificar propriedade
        autor_seguido = get_object_or_404(
            AutorSeguido,
            id=seguidor_id,
            autor=request.user
        )

        # Verificar se já é leitor especial
        if autor_seguido.is_leitor_especial:
            return HttpResponse('Este seguidor já é um leitor especial', status=400)

        # Marcar como leitor especial
        autor_seguido.is_leitor_especial = True
        autor_seguido.save(update_fields=['is_leitor_especial'])

        # Criar notificação para o seguidor
        username_autor = request.user.username

        criar_notificacao(
            usuario_destino=autor_seguido.seguidor,
            motivo_codigo='SELO_LEITOR_ESPECIAL',
            texto=f'@{username_autor} concedeu a você o selo de leitor especial!',
            link_destino=reverse('perfil_publico', kwargs={'username': username_autor}),
            usuario_origem=request.user
        )

        # Adicionar mensagem de sucesso
        messages.success(request, f'{autor_seguido.seguidor.get_full_name()} recebeu o Selo de Leitor Especial!')

        # Calcular estatísticas do seguidor
        autor_seguido.estatisticas = calcular_estatisticas_seguidor(
            seguidor=autor_seguido.seguidor,
            autor=request.user
        )

        # Renderizar o card atualizado com RequestContext para incluir processadores de contexto
        html = render_to_string('painel_autor/_card_seguidor.html', {
            'autor_seguido': autor_seguido,
            'seguidor': autor_seguido.seguidor,
        }, request=request)

        return HttpResponse(html, status=200)

    except AutorSeguido.DoesNotExist:
        return HttpResponse('Seguidor não encontrado', status=404)
    except Exception as e:
        return HttpResponse(f'Erro ao marcar seguidor: {str(e)}', status=500)


@autor_required
def desmarcar_leitor_especial(request, seguidor_id):
    """
    ETAPA 5 - Sistema de Selos de Leitor Especial.

    Endpoint para desmarcar um seguidor como "leitor especial".

    Ações:
    1. Busca o relacionamento AutorSeguido
    2. Verifica se o autor logado é o dono do relacionamento
    3. Marca is_leitor_especial = False
    4. Marca selo_especial_modal_exibido = False (reset para caso seja marcado novamente)
    5. NÃO cria notificação (conforme especificação)
    6. Retorna HTML atualizado do card para HTMX

    Args:
        request: HttpRequest
        seguidor_id (int): ID do relacionamento AutorSeguido

    Returns:
        HttpResponse com HTML do card atualizado
    """
    from django.template.loader import render_to_string

    if request.method != 'POST':
        return HttpResponse('Método não permitido', status=405)

    try:
        # Buscar relacionamento e verificar propriedade
        autor_seguido = get_object_or_404(
            AutorSeguido,
            id=seguidor_id,
            autor=request.user
        )

        # Verificar se NÃO é leitor especial
        if not autor_seguido.is_leitor_especial:
            return HttpResponse('Este seguidor não é um leitor especial', status=400)

        # Desmarcar leitor especial e resetar flag de modal
        autor_seguido.is_leitor_especial = False
        autor_seguido.selo_especial_modal_exibido = False
        autor_seguido.save(update_fields=['is_leitor_especial', 'selo_especial_modal_exibido'])

        # Adicionar mensagem de sucesso
        messages.success(request, f'O Selo de Leitor Especial de {autor_seguido.seguidor.get_full_name()} foi removido.')

        # Calcular estatísticas do seguidor
        autor_seguido.estatisticas = calcular_estatisticas_seguidor(
            seguidor=autor_seguido.seguidor,
            autor=request.user
        )

        # Renderizar o card atualizado com RequestContext para incluir processadores de contexto
        html = render_to_string('painel_autor/_card_seguidor.html', {
            'autor_seguido': autor_seguido,
            'seguidor': autor_seguido.seguidor,
        }, request=request)

        return HttpResponse(html, status=200)

    except AutorSeguido.DoesNotExist:
        return HttpResponse('Seguidor não encontrado', status=404)
    except Exception as e:
        return HttpResponse(f'Erro ao desmarcar seguidor: {str(e)}', status=500)


@autor_required
def remover_seguidor(request, seguidor_id):
    """
    ETAPA 6 - Sistema de Selos de Leitor Especial.

    Endpoint para remover um seguidor (DELETE do relacionamento AutorSeguido).

    Ações:
    1. Busca o relacionamento AutorSeguido
    2. Verifica se o autor logado é o dono do relacionamento
    3. Deleta o registro
    4. Retorna resposta vazia (card será removido via HTMX swap outerHTML)

    Args:
        request: HttpRequest
        seguidor_id (int): ID do relacionamento AutorSeguido

    Returns:
        HttpResponse vazio com status 200 (HTMX removerá o card)
    """
    if request.method != 'POST':
        return HttpResponse('Método não permitido', status=405)

    try:
        # Buscar relacionamento e verificar propriedade
        autor_seguido = get_object_or_404(
            AutorSeguido,
            id=seguidor_id,
            autor=request.user
        )

        # Guardar nome para mensagem
        nome_seguidor = autor_seguido.seguidor.get_full_name()

        # Deletar relacionamento
        autor_seguido.delete()

        # Adicionar mensagem de sucesso
        messages.success(request, f'{nome_seguidor} foi removido dos seus seguidores.')

        # Retornar resposta vazia (HTMX removerá o card via swap outerHTML)
        return HttpResponse('', status=200)

    except AutorSeguido.DoesNotExist:
        return HttpResponse('Seguidor não encontrado', status=404)
    except Exception as e:
        return HttpResponse(f'Erro ao remover seguidor: {str(e)}', status=500)


@autor_required
def ver_comentarios_seguidor(request, seguidor_id):
    """
    Endpoint para visualizar todos os comentários de um seguidor específico
    nos textos do autor logado.

    Retorna JSON com:
    - nome_seguidor: Nome completo do seguidor
    - textos: Lista de textos (mais recentes primeiro) com seus comentários

    Args:
        request: HttpRequest
        seguidor_id (int): ID do relacionamento AutorSeguido

    Returns:
        JsonResponse com dados dos comentários organizados por texto
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Método não permitido'}, status=405)

    try:
        # Buscar relacionamento e verificar propriedade
        autor_seguido = get_object_or_404(
            AutorSeguido,
            id=seguidor_id,
            autor=request.user
        )

        seguidor = autor_seguido.seguidor

        # Buscar todos os comentários APROVADOS desse seguidor nos textos do autor
        comentarios = Comentario.objects.filter(
            autor=seguidor,
            texto__autor=request.user,
            status=Comentario.Status.APROVADO
        ).select_related('texto').order_by('-data_publicacao')

        # Agrupar comentários por texto
        textos_dict = {}
        for comentario in comentarios:
            texto_id = comentario.texto.id
            if texto_id not in textos_dict:
                textos_dict[texto_id] = {
                    'titulo': comentario.texto.titulo,
                    'data_publicacao': comentario.texto.data_publicacao,
                    'comentarios': []
                }
            textos_dict[texto_id]['comentarios'].append({
                'conteudo': comentario.conteudo,
                'data_publicacao': comentario.data_publicacao.strftime('%d/%m/%Y às %H:%M')
            })

        # Converter dict para lista e ordenar por data de publicação do texto (mais recentes primeiro)
        textos_lista = []
        for texto_id, dados in textos_dict.items():
            textos_lista.append({
                'titulo': dados['titulo'],
                'data_publicacao': dados['data_publicacao'],
                'comentarios': dados['comentarios']
            })

        # Ordenar por data de publicação (mais recentes primeiro)
        textos_lista.sort(key=lambda x: x['data_publicacao'], reverse=True)

        return JsonResponse({
            'nome_seguidor': seguidor.get_full_name(),
            'total_comentarios': comentarios.count(),
            'textos': textos_lista
        })

    except AutorSeguido.DoesNotExist:
        return JsonResponse({'error': 'Seguidor não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Erro ao buscar comentários: {str(e)}'}, status=500)


@autor_required
def monetizacao_view(request):
    """
    Item 1 do ROADMAP - Sistema de Monetização via PIX.

    Tela para cadastro/edição/remoção de chave PIX do autor.

    REFATORADO: Usa o modelo MonetizacaoPix separado (não mais campos no User).

    Funcionalidades:
    - GET: Exibe formulário (preenche campos se já tem PIX cadastrado)
    - POST: Processa formulário, valida, salva dados PIX, cria log de auditoria
    - Captura IP do usuário para auditoria
    - Permite remoção completa da chave PIX

    Auditoria:
    - Cria registro em Log para cada operação (INCLUSAO, ALTERACAO, REMOCAO)
    - Registra IP do usuário para fins de segurança e investigação de fraudes

    Args:
        request: HttpRequest

    Returns:
        HttpResponse renderizando template com formulário
    """
    from .forms import MonetizacaoForm
    from apps.usuarios.models import Log, TipoLog, MonetizacaoPix

    # Capturar IP do usuário (para auditoria)
    def get_client_ip(request):
        """Captura o IP real do cliente, considerando proxies."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    user = request.user

    # Buscar MonetizacaoPix existente (ou None se não existe)
    try:
        monetizacao = user.monetizacao_pix
    except MonetizacaoPix.DoesNotExist:
        monetizacao = None

    # POST: Processar formulário
    if request.method == 'POST':
        # Verificar se é uma solicitação de remoção
        if 'remover_chave' in request.POST:
            # Verificar se usuário tem chave cadastrada
            if monetizacao:
                # Buscar ou criar tipo de log PIX_REMOCAO
                tipo_log_remocao, _ = TipoLog.objects.get_or_create(
                    codigo='PIX_REMOCAO',
                    defaults={
                        'nome': 'Remoção de chave PIX',
                        'descricao': 'Registro de remoção de chave PIX do sistema de monetização'
                    }
                )

                # Criar log de remoção (antes de deletar)
                Log.objects.create(
                    usuario=user,
                    tipo_log=tipo_log_remocao,
                    dados={
                        'tipo_chave_pix': monetizacao.tipo_chave_pix,
                        'chave_pix': monetizacao.chave_pix,
                        'pix_nome_completo': monetizacao.pix_nome_completo,
                        'pix_nome_banco': monetizacao.pix_nome_banco,
                        'pix_valor_padrao': str(monetizacao.pix_valor_padrao) if monetizacao.pix_valor_padrao else None
                    },
                    ip_address=get_client_ip(request)
                )

                # Deletar o registro de MonetizacaoPix
                monetizacao.delete()

                messages.success(request, 'Chave PIX removida com sucesso! Seus leitores não verão mais a opção de doação.')
                return redirect('painel_autor:monetizacao')
            else:
                messages.error(request, 'Você não possui chave PIX cadastrada.')
                return redirect('painel_autor:monetizacao')

        # Processar formulário de cadastro/edição
        form = MonetizacaoForm(request.POST)

        if form.is_valid():
            # Verificar se é inclusão ou alteração
            tem_chave_cadastrada = monetizacao is not None

            # Criar ou atualizar MonetizacaoPix
            if monetizacao:
                # ALTERAÇÃO: Atualizar registro existente
                monetizacao.tipo_chave_pix = form.cleaned_data['tipo_chave_pix']
                monetizacao.chave_pix = form.cleaned_data['chave_pix']
                monetizacao.pix_nome_completo = form.cleaned_data['pix_nome_completo']
                monetizacao.pix_nome_banco = form.cleaned_data['pix_nome_banco']
                monetizacao.pix_codigo_banco = form.cleaned_data.get('pix_codigo_banco')
                monetizacao.pix_valor_padrao = form.cleaned_data.get('pix_valor_padrao')
                monetizacao.pix_valor_padrao_informado = form.cleaned_data.get('pix_valor_padrao_informado', False)

                # Aceites: se já foram marcados uma vez (True no banco), não precisa marcar novamente
                if not monetizacao.pix_aceite_termos:
                    if not form.cleaned_data.get('aceite_termos', False):
                        messages.error(request, 'Você precisa aceitar os termos de uso para cadastrar uma chave PIX.')
                        return redirect('painel_autor:monetizacao')
                    monetizacao.pix_aceite_termos = True

                if not monetizacao.pix_aceite_responsabilidade:
                    if not form.cleaned_data.get('aceite_responsabilidade', False):
                        messages.error(request, 'Você precisa declarar que a chave PIX é sua para cadastrar.')
                        return redirect('painel_autor:monetizacao')
                    monetizacao.pix_aceite_responsabilidade = True

                monetizacao.save()

            else:
                # INCLUSÃO: Criar novo registro
                # Validar aceites (obrigatórios na primeira vez)
                if not form.cleaned_data.get('aceite_termos', False):
                    messages.error(request, 'Você precisa aceitar os termos de uso para cadastrar uma chave PIX.')
                    return redirect('painel_autor:monetizacao')

                if not form.cleaned_data.get('aceite_responsabilidade', False):
                    messages.error(request, 'Você precisa declarar que a chave PIX é sua para cadastrar.')
                    return redirect('painel_autor:monetizacao')

                monetizacao = MonetizacaoPix.objects.create(
                    autor=user,
                    tipo_chave_pix=form.cleaned_data['tipo_chave_pix'],
                    chave_pix=form.cleaned_data['chave_pix'],
                    pix_nome_completo=form.cleaned_data['pix_nome_completo'],
                    pix_nome_banco=form.cleaned_data['pix_nome_banco'],
                    pix_codigo_banco=form.cleaned_data.get('pix_codigo_banco'),
                    pix_valor_padrao=form.cleaned_data.get('pix_valor_padrao'),
                    pix_valor_padrao_informado=form.cleaned_data.get('pix_valor_padrao_informado', False),
                    pix_aceite_termos=True,
                    pix_aceite_responsabilidade=True,
                )

            # Criar log de auditoria
            if tem_chave_cadastrada:
                tipo_log, _ = TipoLog.objects.get_or_create(
                    codigo='PIX_ALTERACAO',
                    defaults={
                        'nome': 'Alteração de chave PIX',
                        'descricao': 'Registro de alteração de chave PIX do sistema de monetização'
                    }
                )
            else:
                tipo_log, _ = TipoLog.objects.get_or_create(
                    codigo='PIX_INCLUSAO',
                    defaults={
                        'nome': 'Inclusão de chave PIX',
                        'descricao': 'Registro de cadastro inicial de chave PIX no sistema de monetização'
                    }
                )

            Log.objects.create(
                usuario=user,
                tipo_log=tipo_log,
                dados={
                    'tipo_chave_pix': monetizacao.tipo_chave_pix,
                    'chave_pix': monetizacao.chave_pix,
                    'pix_nome_completo': monetizacao.pix_nome_completo,
                    'pix_nome_banco': monetizacao.pix_nome_banco,
                    'pix_valor_padrao': str(monetizacao.pix_valor_padrao) if monetizacao.pix_valor_padrao else None
                },
                ip_address=get_client_ip(request)
            )

            # Mensagem de sucesso
            if tem_chave_cadastrada:
                messages.success(request, 'Chave PIX atualizada com sucesso! As alterações já estão visíveis para seus leitores.')
            else:
                messages.success(request, 'Chave PIX cadastrada com sucesso! Agora seus leitores podem fazer doações voluntárias.')

            return redirect('painel_autor:monetizacao')

    # GET: Exibir formulário
    else:
        # Preencher formulário com dados existentes (se houver)
        initial_data = {}
        if monetizacao:
            # Se for telefone e começar com +55, remover o +55 para exibição no formulário
            # O +55 será adicionado automaticamente ao salvar
            chave_pix_display = monetizacao.chave_pix
            if monetizacao.tipo_chave_pix == 'TELEFONE' and monetizacao.chave_pix.startswith('+55'):
                chave_pix_display = monetizacao.chave_pix[3:]  # Remove os 3 primeiros caracteres (+55)

            initial_data = {
                'tipo_chave_pix': monetizacao.tipo_chave_pix,
                'chave_pix': chave_pix_display,
                'pix_nome_completo': monetizacao.pix_nome_completo,
                'pix_nome_banco': monetizacao.pix_nome_banco,
                'pix_codigo_banco': monetizacao.pix_codigo_banco,
                'pix_valor_padrao': monetizacao.pix_valor_padrao,
                'pix_valor_padrao_informado': monetizacao.pix_valor_padrao_informado,
                # Aceites não precisam ser preenchidos novamente (já foram aceitos uma vez)
            }

        form = MonetizacaoForm(initial=initial_data)

    # Contexto para o template
    context = {
        'form': form,
        'tem_chave_cadastrada': monetizacao is not None,
        'chave_atual': monetizacao.chave_pix if monetizacao else None,
        'tipo_chave_atual': monetizacao.get_tipo_chave_pix_display() if monetizacao else None,
        'monetizacao': monetizacao,  # Passar objeto completo para template
    }

    return render(request, 'painel_autor/monetizacao.html', context)


# ====================================================================
# CONVIDAR NOVO AUTOR
# ====================================================================

@autor_required
def convidar_autor_view(request):
    """
    View para um autor convidar outro autor para a plataforma.

    Funcionalidades:
    - GET: Exibe formulário para preenchimento dos dados do novo autor
    - POST: Valida dados, cria o novo autor, gera convite e envia e-mail automaticamente

    O novo autor recebe:
    1. Conta criada com is_active=False
    2. ConviteAutor com token único (7 dias de validade)
    3. E-mail de convite com link de ativação

    O fluxo é o mesmo do painel admin, mas com:
    - Tipo de autor fixo como "contemporâneo"
    - E-mail de convite enviado automaticamente
    - Informação de quem convidou no e-mail
    - Limite de convites por autor (configurável pelo admin)
    """
    from apps.core.utils import enviar_email_convite_autor
    from apps.painel_admin.models import ConfiguracaoSistema

    # Obter configuração do sistema
    config = ConfiguracaoSistema.get_config()
    limite_convites = config.limite_convites_autor

    # Contar TODOS os convites enviados (decrementa ao enviar, não ao aceitar)
    convites_utilizados = ConviteAutor.objects.filter(
        convidado_por=request.user
    ).count()
    convites_restantes = max(0, limite_convites - convites_utilizados)

    # Verificar se tem convites disponíveis
    sem_convites = convites_restantes == 0

    # Buscar convites pendentes (enviados mas não aceitos ainda)
    convites_pendentes = ConviteAutor.objects.filter(
        convidado_por=request.user,
        ativado=False
    ).select_related('autor').order_by('-data_criacao')

    # Buscar convites aceitos (autores que aceitaram o convite)
    convites_aceitos = ConviteAutor.objects.filter(
        convidado_por=request.user,
        ativado=True
    ).select_related('autor').order_by('-data_criacao')

    if request.method == 'POST':
        # Bloquear se não tiver convites
        if sem_convites:
            messages.error(
                request,
                'Você já usou todos os seus convites para convidar novos autores.'
            )
            return redirect('painel_autor:convidar_autor')

        form = NovoAutorForm(request.POST, request.FILES)

        if form.is_valid():
            # Criar o novo autor (similar ao painel admin)
            novo_autor = form.save(commit=False)

            # Configurar campos obrigatórios
            novo_autor.role = User.Role.AUTOR
            novo_autor.is_active = False  # Inativo até ativar via link

            # Processar nome completo
            nome_completo = form.cleaned_data.get('nome_completo', '').strip()
            partes_nome = nome_completo.split()
            if len(partes_nome) >= 2:
                novo_autor.first_name = partes_nome[0]
                novo_autor.last_name = ' '.join(partes_nome[1:])
            else:
                novo_autor.first_name = nome_completo
                novo_autor.last_name = ''

            # Configurar país e sexo
            novo_autor.pais = form.cleaned_data.get('pais', 'Brasil')
            novo_autor.sexo = form.cleaned_data.get('sexo', 'N')

            # Tipo de autor sempre "contemporâneo" para convites de autores
            novo_autor.tipo_autor = 'contemporaneo'

            # Senha temporária (autor definirá na ativação)
            import uuid
            novo_autor.password = uuid.uuid4().hex

            # Tratar remoção de foto
            if form.cleaned_data.get('remover_foto'):
                if novo_autor.foto:
                    novo_autor.foto.delete(save=False)
                novo_autor.foto = None

            # Salvar o autor
            novo_autor.save()

            # Criar convite com token único (registrando quem convidou)
            convite = ConviteAutor.objects.create(
                autor=novo_autor,
                convidado_por=request.user,  # Registrar quem fez o convite
                data_expiracao=timezone.now() + timezone.timedelta(days=7)
            )

            # Enviar e-mail de convite automaticamente
            email_enviado = enviar_email_convite_autor(
                convite=convite,
                autor_convidante=request.user,
                request=request
            )

            if email_enviado:
                messages.success(
                    request,
                    f'Convite enviado com sucesso para {novo_autor.email}! '
                    f'O autor {novo_autor.get_full_name()} receberá um e-mail com o link de ativação.'
                )
                return redirect('painel_autor:convidar_autor')
            else:
                # E-mail falhou, mas convite foi criado - mostrar link em modal
                link_convite = convite.get_link_ativacao(request)
                # Atualizar listas de convites (refetch após criação)
                convites_pendentes = ConviteAutor.objects.filter(
                    convidado_por=request.user,
                    ativado=False
                ).select_related('autor').order_by('-data_criacao')
                convites_aceitos = ConviteAutor.objects.filter(
                    convidado_por=request.user,
                    ativado=True
                ).select_related('autor').order_by('-data_criacao')
                # Recalcular convites (agora com o novo convite)
                convites_utilizados = ConviteAutor.objects.filter(convidado_por=request.user).count()
                convites_restantes = max(0, limite_convites - convites_utilizados)
                sem_convites = convites_restantes == 0
                # Renderizar a mesma página com modal aberta
                context = {
                    'form': NovoAutorForm(),  # Formulário limpo
                    'mostrar_modal_link': True,
                    'link_convite': link_convite,
                    'nome_autor_convidado': novo_autor.get_full_name(),
                    'email_autor_convidado': novo_autor.email,
                    'convites_restantes': convites_restantes,
                    'limite_convites': limite_convites,
                    'convites_utilizados': convites_utilizados,
                    'sem_convites': sem_convites,
                    'convites_pendentes': convites_pendentes,
                    'convites_aceitos': convites_aceitos,
                }
                return render(request, 'painel_autor/convidar_autor.html', context)

    else:
        # GET: Formulário vazio
        form = NovoAutorForm()

    context = {
        'form': form,
        'convites_restantes': convites_restantes,
        'limite_convites': limite_convites,
        'convites_utilizados': convites_utilizados,
        'sem_convites': sem_convites,
        'convites_pendentes': convites_pendentes,
        'convites_aceitos': convites_aceitos,
    }

    return render(request, 'painel_autor/convidar_autor.html', context)
