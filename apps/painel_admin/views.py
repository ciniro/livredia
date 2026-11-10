"""
Views do painel administrativo.
"""
from django.views.generic import TemplateView, CreateView, UpdateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.db.models import Count, Q, Sum, Avg, F
from django.db import models

from apps.usuarios.models import User
from apps.textos.models import Texto, Tag
from apps.comentarios.models import Comentario
from apps.core.models import PaginaEstatica
from apps.painel_autor.models import ConfiguracaoAutor
from .decorators import admin_required
from .models import ConviteAutor, ContatoAdministrativo
from .forms import (
    NovoAutorForm, AtivarAutorForm, EditarLeitorForm, EditarPaginaForm,
    NovoAdminForm, EditarAdminForm, ContatoAdministrativoForm,
    PersonalizacaoAutorForm
)


@method_decorator(admin_required, name='dispatch')
class AdminDashboardView(TemplateView):
    """
    Dashboard do administrador com métricas principais da plataforma.

    Exibe:
    - Boas-vindas ao administrador logado (com foto e data de cadastro)
    - Estatísticas globais da plataforma (visualizações totais e média por texto)
    - Total de Autores cadastrados
    - Total de Leitores cadastrados
    - Total de Textos Publicados
    - Total de Comentários Pendentes de moderação
    """
    template_name = 'painel_admin/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # ===== DADOS DO ADMINISTRADOR =====
        context['admin_nome'] = user.first_name
        context['data_cadastro'] = user.date_joined.strftime('%d/%m/%Y')

        # ===== ESTATÍSTICAS GLOBAIS DA PLATAFORMA =====
        from apps.textos.models import Visualizacao
        from apps.textos.views import formatar_tempo_leitura
        from django.db.models import Sum

        # Total de visualizações na plataforma
        total_visualizacoes_plataforma = Visualizacao.objects.all().count()
        context['total_visualizacoes_plataforma'] = total_visualizacoes_plataforma

        # Média de visualizações por texto publicado
        textos_publicados_count = Texto.objects.filter(status=Texto.Status.PUBLICADO).count()
        if textos_publicados_count > 0:
            context['media_visualizacoes_plataforma'] = round(total_visualizacoes_plataforma / textos_publicados_count, 1)
        else:
            context['media_visualizacoes_plataforma'] = 0

        # Tempo total de leitura na plataforma
        tempo_total_segundos = Visualizacao.objects.filter(
            tempo_permanencia__isnull=False
        ).aggregate(total=Sum('tempo_permanencia'))['total'] or 0
        context['tempo_total_leitura_plataforma'] = formatar_tempo_leitura(tempo_total_segundos)

        # Tempo médio de leitura por texto publicado
        if textos_publicados_count > 0 and tempo_total_segundos > 0:
            tempo_medio_segundos = tempo_total_segundos / textos_publicados_count
            context['tempo_medio_leitura_plataforma'] = formatar_tempo_leitura(int(tempo_medio_segundos))
        else:
            context['tempo_medio_leitura_plataforma'] = "0min"

        # ===== MÉTRICAS DE AUTORES =====
        context['total_autores'] = User.objects.filter(role=User.Role.AUTOR).count()
        context['autores_ativos'] = User.objects.filter(role=User.Role.AUTOR, is_active=True).count()
        context['autores_pendentes'] = User.objects.filter(role=User.Role.AUTOR, is_active=False).count()
        context['autores_suspensos'] = User.objects.filter(role=User.Role.AUTOR, is_suspended=True).count()
        context['autores_nao_suspensos'] = User.objects.filter(role=User.Role.AUTOR, is_suspended=False).count()

        # ===== MÉTRICAS DE LEITORES =====
        context['total_leitores'] = User.objects.filter(role=User.Role.LEITOR).count()
        context['leitores_verificados'] = User.objects.filter(role=User.Role.LEITOR, email_verified=True).count()
        context['leitores_nao_verificados'] = User.objects.filter(role=User.Role.LEITOR, email_verified=False).count()
        context['leitores_suspensos'] = User.objects.filter(role=User.Role.LEITOR, is_suspended=True).count()
        context['leitores_nao_suspensos'] = User.objects.filter(role=User.Role.LEITOR, is_suspended=False).count()

        # ===== MÉTRICAS DE TEXTOS =====
        context['textos_publicados'] = Texto.objects.filter(status=Texto.Status.PUBLICADO).count()
        context['textos_rascunho'] = Texto.objects.filter(status=Texto.Status.RASCUNHO).count()
        context['textos_suspensos'] = Texto.objects.filter(is_suspended=True).count()
        context['textos_ativos'] = Texto.objects.filter(status=Texto.Status.PUBLICADO, is_suspended=False).count()

        # ===== MÉTRICAS DE COMENTÁRIOS =====
        context['total_comentarios'] = Comentario.objects.count()
        context['comentarios_pendentes'] = Comentario.objects.filter(status=Comentario.Status.PENDENTE).count()
        context['comentarios_aprovados'] = Comentario.objects.filter(status=Comentario.Status.APROVADO).count()
        context['comentarios_rejeitados'] = Comentario.objects.filter(status=Comentario.Status.REJEITADO).count()
        context['comentarios_anonimos'] = Comentario.objects.filter(publicado_anonimamente=True).count()

        return context


@method_decorator(admin_required, name='dispatch')
class AdminAutorCreateView(CreateView):
    """
    View para cadastro de novo autor pelo administrador.

    Cria um novo usuário com role=AUTOR e is_active=False, gera um
    ConviteAutor com token único (expiração 7 dias) e redireciona
    para a listagem de autores com mensagem de sucesso.
    """
    model = User
    form_class = NovoAutorForm
    template_name = 'painel_admin/novo_autor.html'
    success_url = reverse_lazy('painel_admin:gestao_autores')

    def form_valid(self, form):
        """
        Salva o autor, cria o convite (sem exibir link) e redireciona.
        O link de boas-vindas será gerado depois na tela de listagem.
        """
        # Salvar o autor
        self.object = form.save()

        # Mensagem de sucesso (usando toastr)
        messages.success(
            self.request,
            'Autor salvo com sucesso.'
        )

        return super().form_valid(form)

    def form_invalid(self, form):
        """
        Adiciona mensagem de erro se o formulário for inválido.
        """
        messages.error(
            self.request,
            'Houve um erro ao cadastrar o autor. Por favor, corrija os erros abaixo.'
        )
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        """
        Retorna contexto padrão do formulário.
        """
        context = super().get_context_data(**kwargs)
        return context


@method_decorator(admin_required, name='dispatch')
class AdminAutorEditView(UpdateView):
    """
    View para edição de autor existente pelo administrador.

    Permite ao admin atualizar todos os dados do autor (exceto senha).
    Reutiliza o mesmo formulário e template do cadastro.
    """
    model = User
    form_class = NovoAutorForm
    template_name = 'painel_admin/novo_autor.html'
    success_url = reverse_lazy('painel_admin:gestao_autores')
    pk_url_kwarg = 'pk'
    context_object_name = 'autor_sendo_editado'  # Evita sobrescrever 'user' do request.user

    def get_queryset(self):
        """Retorna apenas usuários com role=AUTOR."""
        return User.objects.filter(role=User.Role.AUTOR)

    def form_valid(self, form):
        """
        Salva alterações do autor e redireciona.
        Não altera a senha (autor já possui senha definida).
        """
        # Salvar o autor
        self.object = form.save()

        # Mensagem de sucesso
        messages.success(
            self.request,
            f'Dados de {self.object.get_display_name()} atualizados com sucesso.'
        )

        return redirect(self.success_url)

    def form_invalid(self, form):
        """
        Adiciona mensagem de erro se o formulário for inválido.
        """
        messages.error(
            self.request,
            'Houve um erro ao atualizar o autor. Por favor, corrija os erros abaixo.'
        )
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        """
        Adiciona contexto indicando que é edição (não cadastro).
        """
        context = super().get_context_data(**kwargs)
        context['editando'] = True
        context['autor_editado'] = self.object
        return context


def convite_autor_view(request, token):
    """
    Página de boas-vindas ao autor (via link de ativação).

    GET: Exibe formulário para autor confirmar dados e definir senha
    POST: Processa formulário, ativa conta e redireciona para login
    """
    # Buscar convite pelo token
    convite = get_object_or_404(ConviteAutor, token=token)

    # Verificar se token está expirado
    if convite.expirado():
        messages.error(
            request,
            'Este link de ativação expirou. Entre em contato com o administrador '
            'para solicitar um novo link.'
        )
        return render(request, 'painel_admin/convite_expirado.html', {
            'convite': convite
        })

    # Verificar se convite já foi ativado
    if convite.ativado:
        messages.info(
            request,
            'Este link de ativação já foi utilizado. '
            'Faça login com seu e-mail e senha.'
        )
        return redirect('usuarios:login')

    autor = convite.autor

    if request.method == 'POST':
        form = AtivarAutorForm(request.POST, request.FILES, instance=autor)

        if form.is_valid():
            # Salvar autor (já ativa is_active=True e define senha)
            autor_ativado = form.save()

            # Marcar convite como ativado
            convite.ativado = True
            convite.save()

            # Fazer login automático do autor
            login(request, autor_ativado, backend='apps.usuarios.backends.EmailBackend')

            # Redirecionar para página de agradecimento (não mostrar mensagem aqui)
            return redirect('painel_admin:autor_boas_vindas')
    else:
        # GET: Exibir formulário preenchido com dados do autor
        form = AtivarAutorForm(instance=autor)

    return render(request, 'painel_admin/convite_autor.html', {
        'form': form,
        'autor': autor,
        'convite': convite
    })


# ========================================
# VIEWS PLACEHOLDER (Em Construção)
# ========================================
# Estas views serão implementadas nas próximas telas do projeto.
# Por enquanto, retornam mensagens de "Em construção" para evitar erros 404.

@method_decorator(admin_required, name='dispatch')
class GestaoAutoresListView(ListView):
    """
    Tela 17 - Gestão de Autores (Listagem).

    Exibe listagem completa de autores com:
    - Foto (avatar)
    - Nome do autor
    - Cadastrado desde (data)
    - Textos publicados (count)
    - Status (Ativo/Pendente)
    - Ações (suspender/reativar, excluir, gerar link de boas-vindas)
    """
    model = User
    template_name = 'painel_admin/gestao_autores.html'
    context_object_name = 'autores'
    paginate_by = 30  # Padrão

    def get_paginate_by(self, queryset):
        """
        Permite ao usuário escolher quantos autores exibir por página.
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
        Retorna apenas usuários com role=AUTOR, anotados com:
        - total_textos_publicados (count de textos com status=PUBLICADO)
        - tempo_total_leitura (soma do tempo de permanência em visualizações)
        - tempo_medio_leitura (média do tempo de permanência em visualizações)

        Filtros:
        - Busca por nome (first_name, last_name, pseudonimo)

        Ordenação:
        - nome (alfabética A-Z ou Z-A)
        - cadastro (mais recente ou mais antigo)
        - textos (maior ou menor)
        - status (pendente primeiro ou ativo primeiro)
        - tempo_total_leitura (maior ou menor)
        - tempo_medio_leitura (maior ou menor)
        """
        queryset = User.objects.filter(role=User.Role.AUTOR).annotate(
            total_textos_publicados=Count(
                'textos',
                filter=Q(textos__status=Texto.Status.PUBLICADO),
                distinct=True
            ),
            total_visualizacoes=Count('textos__visualizacoes'),  # SEM distinct - conta TODAS as visualizações
            tempo_total_leitura=Sum('textos__visualizacoes__tempo_permanencia'),
            visualizacoes_unicas=Count(
                'textos__visualizacoes__sessao_id',
                filter=Q(textos__visualizacoes__usuario__isnull=False),  # Apenas usuários logados
                distinct=True  # Sem repetir a mesma sessão
            )
        ).select_related().prefetch_related('convite')

        # Filtro de busca por nome
        busca = self.request.GET.get('busca', '').strip()
        if busca:
            queryset = queryset.filter(
                Q(first_name__icontains=busca) |
                Q(last_name__icontains=busca) |
                Q(pseudonimo__icontains=busca)
            )

        # Filtro de esconder clássicos
        esconder_classicos = self.request.GET.get('esconder_classicos', '')
        if esconder_classicos == 'on':
            queryset = queryset.filter(is_classico=False)

        # Ordenação
        order_by = self.request.GET.get('order_by', '-date_joined')

        # Validar campo de ordenação
        valid_orderings = [
            'first_name', '-first_name',  # Nome A-Z / Z-A
            'date_joined', '-date_joined',  # Cadastro antigo → recente / recente → antigo
            'total_textos_publicados', '-total_textos_publicados',  # Textos menor → maior / maior → menor
            'is_active', '-is_active',  # Status pendente primeiro / ativo primeiro
            'tempo_total_leitura', '-tempo_total_leitura',  # Tempo total menor → maior / maior → menor
        ]

        if order_by in valid_orderings:
            queryset = queryset.order_by(order_by)
        else:
            queryset = queryset.order_by('-date_joined')

        return queryset

    def get_context_data(self, **kwargs):
        """
        Adiciona informações extras ao contexto:
        - total_autores: Total de autores cadastrados
        - autores_ativos: Total de autores com is_active=True
        - autores_pendentes: Total de autores com is_active=False
        - busca: Termo de busca atual
        - order_by: Campo de ordenação atual
        - per_page: Quantidade de autores por página
        """
        context = super().get_context_data(**kwargs)

        context['total_autores'] = User.objects.filter(role=User.Role.AUTOR).count()
        context['autores_ativos'] = User.objects.filter(
            role=User.Role.AUTOR,
            is_active=True
        ).count()
        context['autores_pendentes'] = User.objects.filter(
            role=User.Role.AUTOR,
            is_active=False
        ).count()

        # Parâmetros de filtro/ordenação para manter estado
        context['busca'] = self.request.GET.get('busca', '')
        context['order_by'] = self.request.GET.get('order_by', '-date_joined')
        context['per_page'] = self.request.GET.get('per_page', '30')
        context['esconder_classicos'] = self.request.GET.get('esconder_classicos', '')

        return context


@admin_required
def toggle_suspender_autor(request, pk):
    """
    Alterna entre suspender (is_suspended=True) e reativar (is_suspended=False).

    Suspender: Impede login do autor e oculta seu conteúdo no site (mas não deleta do banco)
    Reativar: Permite login do autor e reexibe seu conteúdo no site

    IMPORTANTE: Não altera o status de adesão (is_active), que indica se o autor
    já aceitou o convite inicial (ATIVO/PENDENTE).

    Redireciona de volta à listagem com mensagem de sucesso.
    """
    autor = get_object_or_404(User, pk=pk, role=User.Role.AUTOR)

    # Alternar estado de suspensão
    autor.is_suspended = not autor.is_suspended
    autor.save()

    if autor.is_suspended:
        messages.success(request, f'Autor {autor.get_display_name()} foi suspenso com sucesso.')
    else:
        messages.success(request, f'Autor {autor.get_display_name()} foi reativado com sucesso.')

    return redirect('painel_admin:gestao_autores')


@admin_required
def toggle_admin_autor(request, pk):
    """
    Alterna o flag is_admin entre True e False para um autor.

    DAR ADMIN: Define is_admin=True, permitindo que o autor acesse o painel administrativo
    REMOVER ADMIN: Define is_admin=False, removendo acesso ao painel administrativo

    IMPORTANTE: Apenas autores com role=AUTOR podem receber o flag is_admin.
    Usuários com role=ADMIN já têm acesso total por padrão.

    PROTEÇÃO: Usuário não pode remover permissão administrativa de si mesmo.
    Isso evita que o usuário perca acesso à área administrativa acidentalmente.

    Redireciona de volta à listagem com mensagem de sucesso.
    """
    autor = get_object_or_404(User, pk=pk, role=User.Role.AUTOR)

    # PROTEÇÃO: Impedir que usuário remova admin de si mesmo
    if autor == request.user and autor.is_admin:
        messages.error(
            request,
            'Você não pode remover permissão administrativa de si mesmo. '
            'Peça a outro administrador para fazer isso se necessário.'
        )
        return redirect('painel_admin:gestao_autores')

    # Alternar estado de administrador
    autor.is_admin = not autor.is_admin
    autor.save()

    if autor.is_admin:
        messages.success(request, f'Permissão administrativa concedida a {autor.get_display_name()} com sucesso.')
    else:
        messages.success(request, f'Permissão administrativa removida de {autor.get_display_name()} com sucesso.')

    return redirect('painel_admin:gestao_autores')


@admin_required
def excluir_autor(request, pk):
    """
    Exclui um autor permanentemente (cascata: textos, comentários, convite).
    Redireciona para a listagem com mensagem de sucesso.
    """
    autor = get_object_or_404(User, pk=pk, role=User.Role.AUTOR)

    # Armazenar nome antes de deletar
    nome_autor = autor.get_display_name()

    # Deletar autor (cascata: textos, comentários, convite)
    autor.delete()

    messages.success(request, f'Autor {nome_autor} foi excluído permanentemente.')

    return redirect('painel_admin:gestao_autores')


@admin_required
def gerar_link_boas_vindas(request, pk):
    """
    Gera ou resgata link de boas-vindas para um autor.
    Retorna JSON simples para exibir modal informativo.
    """
    autor = get_object_or_404(User, pk=pk, role=User.Role.AUTOR)

    # Verificar se já existe convite
    convite, created = ConviteAutor.objects.get_or_create(
        autor=autor,
        defaults={
            'data_expiracao': timezone.now() + timezone.timedelta(days=7)
        }
    )

    # Se convite já existe mas expirou, gerar novo token e extender prazo
    if not created and convite.expirado():
        import uuid
        convite.token = str(uuid.uuid4())
        convite.data_expiracao = timezone.now() + timezone.timedelta(days=7)
        convite.ativado = False
        convite.save()

    # Gerar link completo
    link = convite.get_link_ativacao(request)

    messages.success(request, f'Link de boas-vindas gerado para {autor.get_display_name()}.')

    return JsonResponse({
        'status': 'success',
        'message': f'Link de boas-vindas e confirmação gerado para o autor. Por favor, envie este link para o autor confirmar sua adesão à plataforma LIVRE DIA.',
        'link': link,
        'autor_nome': autor.get_display_name()
    })


@login_required
@admin_required
def enviar_convite_email(request, pk):
    """
    Envia e-mail de boas-vindas para um autor.

    Cria ou resgata o ConviteAutor, renova se expirado, e envia o e-mail
    usando a mesma função que já funciona no sistema de convite entre autores.

    Retorna JSON com status de sucesso/erro.
    """
    from apps.core.utils import enviar_email_convite_autor

    autor = get_object_or_404(User, pk=pk, role=User.Role.AUTOR)

    # Verificar se autor já está ativo
    if autor.is_active:
        return JsonResponse({
            'status': 'error',
            'message': f'{autor.get_display_name()} já ativou a conta. Não é necessário enviar convite.'
        }, status=400)

    # Verificar se já existe convite
    convite, created = ConviteAutor.objects.get_or_create(
        autor=autor,
        defaults={
            'data_expiracao': timezone.now() + timezone.timedelta(days=7),
            'convidado_por': None  # Admin não tem autor convidante
        }
    )

    # Se convite já existe mas expirou, gerar novo token e extender prazo
    if not created and convite.expirado():
        import uuid
        convite.token = str(uuid.uuid4())
        convite.data_expiracao = timezone.now() + timezone.timedelta(days=7)
        convite.ativado = False
        convite.save()

    # Enviar e-mail usando a função existente
    email_enviado = enviar_email_convite_autor(
        convite=convite,
        autor_convidante=request.user,  # Admin como convidante
        request=request
    )

    if email_enviado:
        messages.success(
            request,
            f'E-mail de boas-vindas enviado para {autor.get_display_name()} ({autor.email}).'
        )
        return JsonResponse({
            'status': 'success',
            'message': f'E-mail enviado com sucesso para {autor.email}',
            'autor_nome': autor.get_display_name()
        })
    else:
        messages.error(
            request,
            f'Erro ao enviar e-mail para {autor.get_display_name()}. Verifique os logs.'
        )
        return JsonResponse({
            'status': 'error',
            'message': 'Erro ao enviar e-mail. Por favor, tente novamente ou verifique os logs do servidor.'
        }, status=500)


@method_decorator(admin_required, name='dispatch')
class GestaoLeitoresListView(ListView):
    """
    Tela 20 - Gestão de Leitores (Listagem).

    Exibe listagem completa de leitores com:
    - Foto (avatar)
    - Nome do leitor
    - E-mail de login
    - Cidade/País
    - Cadastrado desde (data)
    - Comentários feitos (count)
    - Status de verificação de email (Ativo/Pendente)
    - Ações (editar, excluir, suspender/reativar)
    """
    model = User
    template_name = 'painel_admin/gestao_leitores.html'
    context_object_name = 'leitores'
    paginate_by = 30  # Padrão

    def get_paginate_by(self, queryset):
        """
        Permite ao usuário escolher quantos leitores exibir por página.
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
        Retorna apenas usuários com role=LEITOR, anotados com:
        - total_comentarios (count de comentários)
        - tempo_total_leitura (soma do tempo de permanência em visualizações)
        - tempo_medio_leitura (média do tempo de permanência em visualizações)

        Filtros:
        - Busca por nome (first_name, last_name) ou email

        Ordenação:
        - nome (alfabética A-Z ou Z-A)
        - email (alfabética A-Z ou Z-A)
        - cidade (alfabética A-Z ou Z-A)
        - pais (alfabética A-Z ou Z-A)
        - cadastro (mais recente ou mais antigo)
        - comentarios (maior ou menor)
        - tempo_total_leitura (maior ou menor)
        - tempo_medio_leitura (maior ou menor)
        """
        queryset = User.objects.filter(role=User.Role.LEITOR).annotate(
            total_comentarios=Count('comentarios'),
            total_visualizacoes=Count('visualizacoes'),  # Exibições totais (todas as visualizações)
            visualizacoes_unicas=Count('visualizacoes__texto', distinct=True),  # Visualizações únicas (textos diferentes)
            tempo_total_leitura=Sum('visualizacoes__tempo_permanencia')
        ).select_related()

        # Filtro de busca por nome ou email
        busca = self.request.GET.get('busca', '').strip()
        if busca:
            queryset = queryset.filter(
                Q(first_name__icontains=busca) |
                Q(last_name__icontains=busca) |
                Q(email__icontains=busca)
            )

        # Ordenação
        order_by = self.request.GET.get('order_by', '-date_joined')

        # Validar campo de ordenação
        valid_orderings = [
            'first_name', '-first_name',  # Nome A-Z / Z-A
            'email', '-email',  # Email A-Z / Z-A
            'cidade', '-cidade',  # Cidade A-Z / Z-A
            'pais', '-pais',  # País A-Z / Z-A
            'date_joined', '-date_joined',  # Cadastro antigo → recente / recente → antigo
            'total_comentarios', '-total_comentarios',  # Comentários menor → maior / maior → menor
            'tempo_total_leitura', '-tempo_total_leitura',  # Tempo total menor → maior / maior → menor
        ]

        if order_by in valid_orderings:
            queryset = queryset.order_by(order_by)
        else:
            queryset = queryset.order_by('-date_joined')

        return queryset

    def get_context_data(self, **kwargs):
        """
        Adiciona informações extras ao contexto:
        - total_leitores: Total de leitores cadastrados
        - leitores_ativos: Total de leitores com email_verified=True
        - leitores_pendentes: Total de leitores com email_verified=False
        - busca: Termo de busca atual
        - order_by: Campo de ordenação atual
        - per_page: Quantidade de leitores por página
        """
        context = super().get_context_data(**kwargs)

        context['total_leitores'] = User.objects.filter(role=User.Role.LEITOR).count()
        context['leitores_ativos'] = User.objects.filter(
            role=User.Role.LEITOR,
            email_verified=True
        ).count()
        context['leitores_pendentes'] = User.objects.filter(
            role=User.Role.LEITOR,
            email_verified=False
        ).count()

        # Parâmetros de filtro/ordenação para manter estado
        context['busca'] = self.request.GET.get('busca', '')
        context['order_by'] = self.request.GET.get('order_by', '-date_joined')
        context['per_page'] = self.request.GET.get('per_page', '30')

        return context


@admin_required
def toggle_suspender_leitor(request, pk):
    """
    Alterna entre suspender (is_suspended=True) e reativar (is_suspended=False).

    Suspender: Impede login do leitor e oculta todos seus comentários do site (mas não deleta do banco)
    Reativar: Permite login do leitor e reexibe seus comentários no site

    IMPORTANTE: Não altera o status de verificação de email (email_verified).

    Redireciona de volta à listagem com mensagem de sucesso.
    """
    leitor = get_object_or_404(User, pk=pk, role=User.Role.LEITOR)

    # Alternar estado de suspensão
    leitor.is_suspended = not leitor.is_suspended
    leitor.save()

    if leitor.is_suspended:
        messages.success(request, f'Leitor {leitor.get_full_name()} foi suspenso com sucesso.')
    else:
        messages.success(request, f'Leitor {leitor.get_full_name()} foi reativado com sucesso.')

    return redirect('painel_admin:gestao_leitores')


@admin_required
def excluir_leitor(request, pk):
    """
    Exclui um leitor permanentemente (cascata: comentários).
    Redireciona para a listagem com mensagem de sucesso.
    """
    leitor = get_object_or_404(User, pk=pk, role=User.Role.LEITOR)

    # Armazenar nome antes de deletar
    nome_leitor = leitor.get_full_name()

    # Deletar leitor (cascata: comentários)
    leitor.delete()

    messages.success(request, f'Leitor {nome_leitor} foi excluído permanentemente.')

    return redirect('painel_admin:gestao_leitores')


@method_decorator(admin_required, name='dispatch')
class EditarLeitorView(UpdateView):
    """
    View para edição de leitor existente pelo administrador.

    Permite ao admin atualizar dados do leitor (nome, foto, cidade, país).
    Email não pode ser alterado (é o login).
    Reutiliza template simples de edição.
    """
    model = User
    form_class = EditarLeitorForm
    template_name = 'painel_admin/editar_leitor.html'
    success_url = reverse_lazy('painel_admin:gestao_leitores')
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        """Retorna apenas usuários com role=LEITOR."""
        return User.objects.filter(role=User.Role.LEITOR)

    def form_valid(self, form):
        """
        Salva alterações do leitor e redireciona.
        """
        # Salvar o leitor
        self.object = form.save()

        # Mensagem de sucesso
        messages.success(
            self.request,
            f'Dados de {self.object.get_full_name()} atualizados com sucesso.'
        )

        return redirect(self.success_url)

    def form_invalid(self, form):
        """
        Adiciona mensagem de erro se o formulário for inválido.
        """
        messages.error(
            self.request,
            'Houve um erro ao atualizar o leitor. Por favor, corrija os erros abaixo.'
        )
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        """
        Adiciona contexto indicando que é edição de leitor.
        """
        context = super().get_context_data(**kwargs)
        context['editando'] = True
        context['leitor_editado'] = self.object
        return context


@method_decorator(admin_required, name='dispatch')
class ModeracaoGlobalListView(ListView):
    """
    Tela 19 - Moderação de Comentários (Admin).

    Exibe listagem completa de TODOS os comentários da plataforma (incluindo respostas)
    organizados por status:
    - PENDENTES: Comentários aguardando aprovação (admin pode aprovar/rejeitar)
    - APROVADOS: Comentários já aprovados (decisão do autor é final)
    - REJEITADOS: Comentários já rejeitados (decisão do autor é final)

    Admin tem poder supremo de EXCLUSÃO em qualquer status.

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

        Para requisições HTMX, retorna o partial _tabs_container.html
        que inclui as tabs (com contadores atualizados) e a lista de comentários.
        """
        # Detectar requisição HTMX pelo header HX-Request
        if self.request.headers.get('HX-Request'):
            return ['painel_admin/partials/_tabs_container.html']
        return ['painel_admin/moderacao_global.html']

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
        Retorna TODOS os comentários (incluindo respostas) filtrados por status (tab)
        com select_related para otimização de queries.

        Filtros (todos trabalham em conjunto):
        - status: PENDENTE (padrão), APROVADO, REJEITADO
        - busca_leitor: Busca por nome do leitor (autor do comentário)
        - busca: Busca textual no conteúdo do comentário
        - busca_titulo: Busca por título da obra
        - busca_autor_obra: Busca por nome ou pseudônimo do autor da obra (texto)

        Ordenação:
        - data (mais recente → mais antigo / mais antigo → mais recente)
        - texto (A-Z / Z-A)
        - autor (A-Z / Z-A)

        IMPORTANTE: Exibe 100% dos comentários (incluindo respostas aninhadas).
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

        # Query base: TODOS os comentários (incluindo respostas)
        queryset = Comentario.objects.filter(
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

        # Filtro por autor da obra (nome ou pseudônimo)
        busca_autor_obra = self.request.GET.get('busca_autor_obra', '').strip()
        if busca_autor_obra:
            queryset = queryset.filter(
                Q(texto__autor__first_name__icontains=busca_autor_obra) |
                Q(texto__autor__last_name__icontains=busca_autor_obra) |
                Q(texto__autor__pseudonimo__icontains=busca_autor_obra)
            )

        # Ordenação (padrão: mais recentes primeiro)
        order_by = self.request.GET.get('order_by', '-data_publicacao')

        # Validar campo de ordenação
        valid_orderings = [
            'data_publicacao', '-data_publicacao',  # Data antigo → recente / recente → antigo
            'texto__titulo', '-texto__titulo',  # Texto A-Z / Z-A
            'autor__first_name', '-autor__first_name',  # Autor A-Z / Z-A
        ]

        if order_by in valid_orderings:
            # Sempre ordenar por data de publicação como critério secundário (mais recentes primeiro)
            queryset = queryset.order_by(order_by, '-data_publicacao')
        else:
            # Padrão: mais recentes primeiro
            queryset = queryset.order_by('-data_publicacao')

        return queryset

    def get_context_data(self, **kwargs):
        """
        Adiciona informações extras ao contexto:
        - status_ativa: Status da tab ativa
        - total_pendentes: Total de comentários pendentes (incluindo respostas)
        - total_aprovados: Total de comentários aprovados (incluindo respostas)
        - total_rejeitados: Total de comentários rejeitados (incluindo respostas)
        - busca_leitor, busca, busca_titulo, busca_autor_obra, order_by, per_page: Parâmetros de filtro
        """
        context = super().get_context_data(**kwargs)

        # Status da tab ativa
        context['status_ativa'] = self.request.GET.get('status', Comentario.Status.PENDENTE)

        # Contadores por status (incluindo respostas)
        context['total_pendentes'] = Comentario.objects.filter(
            status=Comentario.Status.PENDENTE
        ).count()
        context['total_aprovados'] = Comentario.objects.filter(
            status=Comentario.Status.APROVADO
        ).count()
        context['total_rejeitados'] = Comentario.objects.filter(
            status=Comentario.Status.REJEITADO
        ).count()

        # Parâmetros de filtro/ordenação para manter estado
        context['busca_leitor'] = self.request.GET.get('busca_leitor', '')
        context['busca'] = self.request.GET.get('busca', '')
        context['busca_titulo'] = self.request.GET.get('busca_titulo', '')
        context['busca_autor_obra'] = self.request.GET.get('busca_autor_obra', '')
        context['order_by'] = self.request.GET.get('order_by', '-data_publicacao')
        context['per_page'] = self.request.GET.get('per_page', '100')

        return context


@admin_required
def aprovar_comentario(request, pk):
    """
    Aprova um comentário PENDENTE (altera status para APROVADO).

    Apenas comentários PENDENTES podem ser aprovados pelo admin.
    Comentários já APROVADOS ou REJEITADOS não podem ter decisão revertida
    (decisão do autor é final).

    Retorna fragment HTML vazio e dispara refresh da página para atualizar contadores.
    """
    comentario = get_object_or_404(Comentario, pk=pk)

    # Verificar se comentário está pendente
    if comentario.status != Comentario.Status.PENDENTE:
        messages.error(request, 'Apenas comentários pendentes podem ser aprovados.')
        return HttpResponse('', status=400)

    # Aprovar comentário
    comentario.status = Comentario.Status.APROVADO
    comentario.save()

    messages.success(request, 'Comentário aprovado com sucesso.')

    # Retornar HTML vazio com header para refresh da página (atualiza contadores)
    response = HttpResponse('')
    response['HX-Refresh'] = 'true'
    return response


@admin_required
def rejeitar_comentario(request, pk):
    """
    Rejeita um comentário PENDENTE (altera status para REJEITADO).

    Apenas comentários PENDENTES podem ser rejeitados pelo admin.
    Comentários já APROVADOS ou REJEITADOS não podem ter decisão revertida
    (decisão do autor é final).

    Retorna fragment HTML vazio e dispara refresh da página para atualizar contadores.
    """
    comentario = get_object_or_404(Comentario, pk=pk)

    # Verificar se comentário está pendente
    if comentario.status != Comentario.Status.PENDENTE:
        messages.error(request, 'Apenas comentários pendentes podem ser rejeitados.')
        return HttpResponse('', status=400)

    # Rejeitar comentário
    comentario.status = Comentario.Status.REJEITADO
    comentario.save()

    messages.success(request, 'Comentário rejeitado com sucesso.')

    # Retornar HTML vazio com header para refresh da página (atualiza contadores)
    response = HttpResponse('')
    response['HX-Refresh'] = 'true'
    return response


@admin_required
def excluir_comentario_admin(request, pk):
    """
    Exclui um comentário permanentemente (PODER SUPREMO do admin).

    Admin pode excluir qualquer comentário, independente do status
    (PENDENTE, APROVADO ou REJEITADO).

    Exclusão em cascata: remove comentário + todas as respostas aninhadas.

    Retorna fragment HTML vazio e dispara refresh da página para atualizar contadores.
    """
    comentario = get_object_or_404(Comentario, pk=pk)

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

    # Retornar HTML vazio com header para refresh da página (atualiza contadores)
    response = HttpResponse('')
    response['HX-Refresh'] = 'true'
    return response


@method_decorator(admin_required, name='dispatch')
class EditarPaginaView(UpdateView):
    """
    Tela 21 - Gestão de Páginas: Edição de Página Estática

    Permite ao admin editar título e conteúdo de uma página estática.
    O slug não pode ser alterado (é a chave primária).

    Usa Quill.js para edição WYSIWYG do conteúdo.
    """
    model = PaginaEstatica
    form_class = EditarPaginaForm
    template_name = 'painel_admin/editar_pagina.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_success_url(self):
        """Retorna para a mesma página após salvar (mostra mensagem de sucesso)"""
        return reverse('painel_admin:editar_pagina', kwargs={'slug': self.object.slug})

    def get_context_data(self, **kwargs):
        """Adiciona dados extras ao contexto do template"""
        context = super().get_context_data(**kwargs)
        context['pagina_titulo'] = f'Editar: {self.object.titulo}'
        context['slug_readonly'] = self.object.slug
        return context

    def form_valid(self, form):
        """Processa formulário válido e exibe mensagem de sucesso"""
        messages.success(
            self.request,
            f'Página "{form.instance.titulo}" atualizada com sucesso!'
        )
        return super().form_valid(form)


@admin_required
def cms_placeholder(request):
    """Placeholder: Tela 21 - Gestão de Páginas (Listagem) - DEPRECATED"""
    return HttpResponse("""
        <html>
        <head><title>Em Construção - LIVRE DIA</title></head>
        <body style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1>🚧 Gestão de Páginas</h1>
            <p>Esta tela está em construção e será implementada em breve.</p>
            <a href="/painel-admin/dashboard/" style="color: #e69019;">← Voltar ao Dashboard</a>
        </body>
        </html>
    """)


def autor_boas_vindas(request):
    """
    Página de boas-vindas após autor aceitar convite.

    Exibe carta de agradecimento, formulário de personalização,
    barra de progresso de 25s, e botão para continuar para o painel do autor.

    Item 8 do ROADMAP: Autor escolhe cor + ícone antes de acessar painel.
    """
    # Verificar se usuário está autenticado e é autor
    if not request.user.is_authenticated or request.user.role != User.Role.AUTOR:
        return redirect('usuarios:login')

    if request.method == 'POST':
        # Processar formulário de personalização (via AJAX)
        form = PersonalizacaoAutorForm(request.POST)

        if form.is_valid():
            # Obter dados do formulário
            cor_background = form.cleaned_data.get('cor_background', '#FDFBF6')
            emoji_marca_dagua = form.cleaned_data.get('emoji_marca_dagua', 'book-open')

            # Obter dados adicionais diretamente do POST (não estão no form)
            tema_plataforma = request.POST.get('tema_plataforma', 'light')
            cor_background_dark = request.POST.get('cor_background_dark', '#1a1a2e')

            # Criar ou atualizar ConfiguracaoAutor com as preferências escolhidas
            ConfiguracaoAutor.objects.update_or_create(
                autor=request.user,
                defaults={
                    'cor_background': cor_background,
                    'cor_background_dark': cor_background_dark,
                    'emoji_marca_dagua': emoji_marca_dagua
                }
            )

            # Salvar tema da plataforma no ConfiguracaoUsuario
            from apps.usuarios.models import ConfiguracaoUsuario
            ConfiguracaoUsuario.objects.update_or_create(
                usuario=request.user,
                defaults={
                    'tema_plataforma': tema_plataforma
                }
            )

            # Retornar resposta JSON de sucesso
            return JsonResponse({'status': 'success'})

        # Se formulário inválido, retornar erro
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    else:
        # GET: Exibir página de boas-vindas com formulário de personalização
        form = PersonalizacaoAutorForm()

        return render(request, 'painel_admin/autor_boas_vindas.html', {
            'autor': request.user,
            'form': form
        })


# ========================================
# GESTÃO DE OBRAS
# ========================================

@method_decorator(admin_required, name='dispatch')
class GestaoObrasListView(ListView):
    """
    View para listagem e gestão de obras/textos publicados.

    Similar ao Acervo de Obras, mas com funcionalidades administrativas:
    - Suspender/Reativar textos
    - Excluir textos permanentemente
    - Filtros de busca e ordenação
    """
    model = Texto
    template_name = 'painel_admin/gestao_obras.html'
    context_object_name = 'textos'
    paginate_by = 30  # Padrão

    def get_paginate_by(self, queryset):
        """
        Permite ao usuário escolher quantas obras exibir por página.
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
        Retorna queryset de textos publicados com filtros aplicados.
        """
        queryset = Texto.objects.filter(
            status=Texto.Status.PUBLICADO
        ).select_related(
            'autor'
        ).prefetch_related(
            'tags'
        ).annotate(
            total_visualizacoes=Count('visualizacoes', distinct=True),
            total_comentarios=Count('comentarios', distinct=True),
            tempo_total_leitura=Sum('visualizacoes__tempo_permanencia'),
            visualizacoes_unicas=Count('visualizacoes__usuario', distinct=True, filter=Q(visualizacoes__usuario__isnull=False))
        )

        # Filtro de busca por título ou subtítulo
        busca_titulo = self.request.GET.get('busca_titulo', '').strip()
        if busca_titulo:
            queryset = queryset.filter(
                Q(titulo__icontains=busca_titulo) |
                Q(subtitulo__icontains=busca_titulo)
            )

        # Filtro por autor ou pseudônimo (busca textual)
        busca_autor = self.request.GET.get('busca_autor', '').strip()
        if busca_autor:
            queryset = queryset.filter(
                Q(autor__first_name__icontains=busca_autor) |
                Q(autor__last_name__icontains=busca_autor) |
                Q(autor__pseudonimo__icontains=busca_autor)
            )

        # Filtro por status de suspensão
        status_suspensao = self.request.GET.get('status_suspensao', '').strip()
        if status_suspensao == 'suspenso':
            queryset = queryset.filter(is_suspended=True)
        elif status_suspensao == 'ativo':
            queryset = queryset.filter(is_suspended=False)
        # Se vazio ou 'todos', não filtra

        # Ordenação
        ordenar = self.request.GET.get('ordenar', '-data_publicacao')
        if ordenar == 'titulo_az':
            queryset = queryset.order_by('titulo')
        elif ordenar == 'titulo_za':
            queryset = queryset.order_by('-titulo')
        elif ordenar == 'autor_az':
            queryset = queryset.order_by('autor__first_name', 'autor__last_name')
        elif ordenar == 'autor_za':
            queryset = queryset.order_by('-autor__first_name', '-autor__last_name')
        elif ordenar == 'data_antigos':
            queryset = queryset.order_by('data_publicacao')
        elif ordenar == '-total_visualizacoes':
            queryset = queryset.order_by('-total_visualizacoes')
        elif ordenar == 'total_visualizacoes':
            queryset = queryset.order_by('total_visualizacoes')
        elif ordenar == '-tempo_total_leitura':
            queryset = queryset.order_by('-tempo_total_leitura')
        elif ordenar == 'tempo_total_leitura':
            queryset = queryset.order_by('tempo_total_leitura')
        else:
            # Padrão: mais recentes primeiro
            queryset = queryset.order_by('-data_publicacao')

        return queryset

    def get_context_data(self, **kwargs):
        """
        Adiciona informações extras ao contexto.
        """
        context = super().get_context_data(**kwargs)

        # Total de obras
        context['total_obras'] = self.get_queryset().count()

        # Contadores de status
        context['total_ativos'] = Texto.objects.filter(
            status=Texto.Status.PUBLICADO,
            is_suspended=False
        ).count()
        context['total_suspensos'] = Texto.objects.filter(
            status=Texto.Status.PUBLICADO,
            is_suspended=True
        ).count()

        # Preservar parâmetros de filtro para paginação
        context['busca_titulo'] = self.request.GET.get('busca_titulo', '')
        context['busca_autor'] = self.request.GET.get('busca_autor', '')
        context['status_suspensao'] = self.request.GET.get('status_suspensao', '')
        context['ordenar'] = self.request.GET.get('ordenar', '-data_publicacao')
        context['per_page'] = self.request.GET.get('per_page', '30')

        return context


@admin_required
def toggle_suspender_texto(request, pk):
    """
    Toggle do status de suspensão de um texto.

    Textos suspensos ficam invisíveis em toda a plataforma:
    - Home
    - Acervo de Obras
    - Pesquisas
    - Galeria de Autores
    """
    texto = get_object_or_404(Texto, pk=pk)

    # Alternar status de suspensão
    texto.is_suspended = not texto.is_suspended
    texto.save()

    # Mensagem de feedback
    if texto.is_suspended:
        messages.success(request, f'Obra "{texto.titulo}" foi suspensa.')
    else:
        messages.success(request, f'Obra "{texto.titulo}" foi reativada.')

    return redirect('painel_admin:gestao_obras')


@admin_required
def excluir_texto(request, pk):
    """
    Exclui um texto permanentemente da plataforma.

    Esta ação é IRREVERSÍVEL e deleta:
    - O texto
    - Todos os comentários vinculados (CASCADE)
    - Todas as visualizações (CASCADE)

    IMPORTANTE: Recomenda-se conversar com o autor antes de excluir.
    """
    texto = get_object_or_404(Texto, pk=pk)

    # Armazenar informações antes de deletar
    titulo_texto = texto.titulo

    # Deletar texto (CASCADE deleta comentários e visualizações)
    texto.delete()

    # Mensagem de confirmação
    messages.success(
        request,
        f'Obra "{titulo_texto}" foi excluída permanentemente da plataforma.'
    )

    return redirect('painel_admin:gestao_obras')


# ========================================
# GESTÃO DE ADMINISTRADORES
# ========================================

@method_decorator(admin_required, name='dispatch')
class GestaoAdministradoresListView(ListView):
    """
    Listagem de todos os usuários com permissões administrativas.

    Exibe:
    - Administradores puros (role=ADMIN)
    - Autores-administradores (role=AUTOR com is_admin=True)

    Regras de permissão:
    - ADMIN puro aparece em cinza e desabilitado (ninguém pode editar)
    - Autor-administrador tem botão REMOVER ADMIN
    - Usuário logado aparece em cinza e desabilitado
    - Apenas ADMIN puro pode:
      - Criar novo admin puro
      - Editar outros admins puros
      - Excluir outros admins puros (mas não a si mesmo)
      - Remover admin de autores-administradores
    """
    model = User
    template_name = 'painel_admin/gestao_administradores.html'
    context_object_name = 'administradores'
    paginate_by = 30

    def get_queryset(self):
        """
        Retorna todos os usuários com permissões administrativas.
        """
        # Buscar todos usuários com is_admin=True (inclui role=ADMIN e role=AUTOR)
        queryset = User.objects.filter(
            Q(role=User.Role.ADMIN) | Q(is_admin=True)
        ).order_by('date_joined')

        return queryset

    def get_context_data(self, **kwargs):
        """Adiciona informações extras ao contexto."""
        context = super().get_context_data(**kwargs)

        # Verificar se usuário logado é ADMIN puro (pode criar novos admins)
        context['can_create_admin'] = (self.request.user.role == User.Role.ADMIN)

        # ID do super admin (nunca pode ser alterado/excluído)
        context['super_admin_pk'] = 1

        return context


@method_decorator(admin_required, name='dispatch')
class NovoAdminView(CreateView):
    """
    Formulário para criar novo administrador puro (role=ADMIN).

    Apenas administradores puros (role=ADMIN) podem acessar.
    """
    model = User
    form_class = NovoAdminForm
    template_name = 'painel_admin/novo_admin.html'
    success_url = reverse_lazy('painel_admin:gestao_administradores')

    def dispatch(self, request, *args, **kwargs):
        """Verifica se usuário é ADMIN puro (apenas eles podem criar admins)."""
        if request.user.role != User.Role.ADMIN:
            messages.error(
                request,
                'Apenas administradores puros podem criar novos administradores.'
            )
            return redirect('painel_admin:gestao_administradores')

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """Cria o admin e exibe mensagem de sucesso."""
        response = super().form_valid(form)

        # Mensagem de sucesso
        messages.success(
            self.request,
            f'Administrador {self.object.get_full_name()} foi criado com sucesso!'
        )

        return response

    def form_invalid(self, form):
        """Adiciona mensagem de erro."""
        messages.error(
            self.request,
            'Houve um erro ao criar o administrador. Corrija os erros abaixo.'
        )
        return super().form_invalid(form)


@method_decorator(admin_required, name='dispatch')
class EditarAdminView(UpdateView):
    """
    Formulário para editar administrador puro (role=ADMIN).

    Apenas administradores puros podem editar outros admins puros.
    Não pode editar a si próprio (use "Minha Conta" para isso).
    """
    model = User
    form_class = EditarAdminForm
    template_name = 'painel_admin/editar_admin.html'
    success_url = reverse_lazy('painel_admin:gestao_administradores')

    def dispatch(self, request, *args, **kwargs):
        """
        Verifica permissões:
        1. Apenas ADMIN puro pode editar
        2. Não pode editar a si próprio
        """
        # Apenas ADMIN puro pode editar
        if request.user.role != User.Role.ADMIN:
            messages.error(
                request,
                'Apenas administradores puros podem editar administradores.'
            )
            return redirect('painel_admin:gestao_administradores')

        # Obter admin a ser editado
        admin = self.get_object()

        # PROTEÇÃO: SUPER ADMIN (PK=1) NUNCA pode ser editado
        if admin.pk == 1:
            messages.error(
                request,
                'O Super Admin não pode ser editado por ninguém. Esta conta está protegida.'
            )
            return redirect('painel_admin:gestao_administradores')

        # Não pode editar a si próprio
        if admin == request.user:
            messages.error(
                request,
                'Você não pode editar seu próprio perfil aqui. Use "Minha Conta" no menu superior.'
            )
            return redirect('painel_admin:gestao_administradores')

        # Apenas pode editar admins puros (role=ADMIN)
        if admin.role != User.Role.ADMIN:
            messages.error(
                request,
                'Você só pode editar administradores puros. Para editar autores-administradores, use "Gestão de Autores".'
            )
            return redirect('painel_admin:gestao_administradores')

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """Salva as alterações e exibe mensagem de sucesso."""
        response = super().form_valid(form)

        messages.success(
            self.request,
            f'Administrador {self.object.get_full_name()} foi atualizado com sucesso!'
        )

        return response

    def form_invalid(self, form):
        """Adiciona mensagem de erro."""
        messages.error(
            self.request,
            'Houve um erro ao atualizar o administrador. Corrija os erros abaixo.'
        )
        return super().form_invalid(form)


@admin_required
def remover_admin_autor(request, pk):
    """
    Remove permissão administrativa de um autor-administrador.

    Apenas administradores (ADMIN puro ou autor-admin) podem executar.
    Remove is_admin=True de autores, voltando-os a autores normais.

    Proteções:
    - Usuário não pode remover admin de si mesmo
    - Só funciona para role=AUTOR com is_admin=True
    - Super Admin (PK=1) está naturalmente protegido (role=ADMIN, não AUTOR)
    """
    # Buscar autor-administrador (Super Admin PK=1 nunca será encontrado aqui - role=ADMIN)
    autor = get_object_or_404(User, pk=pk, role=User.Role.AUTOR, is_admin=True)

    # PROTEÇÃO: Impedir que usuário remova admin de si mesmo
    if autor == request.user:
        messages.error(
            request,
            'Você não pode remover permissão administrativa de si mesmo.'
        )
        return redirect('painel_admin:gestao_administradores')

    # Remover permissão administrativa
    autor.is_admin = False
    autor.save()

    messages.success(
        request,
        f'Permissão administrativa removida de {autor.get_display_name()}. Agora ele é um autor normal.'
    )

    return redirect('painel_admin:gestao_administradores')


@admin_required
def excluir_admin(request, pk):
    """
    Exclui um administrador puro (role=ADMIN) permanentemente.

    Apenas administradores puros (role=ADMIN) podem executar.
    Deleta conta CASCADE (comentários, etc).

    Proteções:
    - Apenas ADMIN puro pode excluir
    - Super Admin (PK=1) NUNCA pode ser excluído
    - Usuário não pode excluir a si mesmo
    - Apenas pode excluir outros admins puros (role=ADMIN)
    """
    # PROTEÇÃO: Apenas ADMIN puro pode excluir
    if request.user.role != User.Role.ADMIN:
        messages.error(
            request,
            'Apenas administradores puros podem excluir administradores.'
        )
        return redirect('painel_admin:gestao_administradores')

    # Buscar admin a ser excluído
    admin = get_object_or_404(User, pk=pk, role=User.Role.ADMIN)

    # PROTEÇÃO: SUPER ADMIN (PK=1) NUNCA pode ser excluído
    if admin.pk == 1:
        messages.error(
            request,
            'O Super Admin não pode ser excluído por ninguém. Esta conta está protegida.'
        )
        return redirect('painel_admin:gestao_administradores')

    # PROTEÇÃO: Impedir auto-exclusão
    if admin == request.user:
        messages.error(
            request,
            'Você não pode excluir a si próprio. Peça a outro administrador para fazer isso se necessário.'
        )
        return redirect('painel_admin:gestao_administradores')

    # Armazenar nome antes de deletar
    nome_admin = admin.get_full_name()

    # Deletar admin (CASCADE deleta comentários se houver)
    admin.delete()

    # Mensagem de confirmação
    messages.success(
        request,
        f'Administrador {nome_admin} foi excluído permanentemente do sistema.'
    )

    return redirect('painel_admin:gestao_administradores')


# ========================================
# GESTÃO DE TEMAS (TAGS)
# ========================================

@method_decorator(admin_required, name='dispatch')
class GestaoTemasListView(ListView):
    """
    Tela de Gestão de Temas (CRUD de Tags).

    Exibe listagem completa de temas/tags com:
    - Nome do tema
    - Quantidade de textos associados
    - Ações (editar, excluir)

    Acessível para administradores e autores-admin.
    """
    model = Tag
    template_name = 'painel_admin/gestao_temas.html'
    context_object_name = 'temas'
    paginate_by = 100

    def get_paginate_by(self, queryset):
        """
        Permite ao usuário escolher quantos temas exibir por página.
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
        Retorna todas as tags anotadas com:
        - total_textos (count de textos associados)

        Filtros:
        - Busca por nome da tag

        Ordenação:
        - nome (alfabética A-Z ou Z-A)
        - textos (maior ou menor quantidade de textos)
        """
        queryset = Tag.objects.annotate(
            total_textos=Count('textos')
        )

        # Filtro de busca por nome
        busca = self.request.GET.get('busca', '').strip()
        if busca:
            queryset = queryset.filter(nome__icontains=busca)

        # Filtro de ordenação
        ordenacao = self.request.GET.get('ordenacao', 'nome_asc')
        if ordenacao == 'nome_asc':
            queryset = queryset.order_by('nome')
        elif ordenacao == 'nome_desc':
            queryset = queryset.order_by('-nome')
        elif ordenacao == 'textos_desc':
            queryset = queryset.order_by('-total_textos', 'nome')
        elif ordenacao == 'textos_asc':
            queryset = queryset.order_by('total_textos', 'nome')
        else:
            queryset = queryset.order_by('nome')

        return queryset

    def get_context_data(self, **kwargs):
        """
        Adiciona ao contexto:
        - Parâmetros de filtro atuais
        - Total de temas
        """
        context = super().get_context_data(**kwargs)

        # Parâmetros de filtro
        context['busca'] = self.request.GET.get('busca', '')
        context['ordenacao'] = self.request.GET.get('ordenacao', 'nome_asc')
        context['per_page'] = self.get_paginate_by(None)

        # Total de temas
        context['total_temas'] = Tag.objects.count()

        return context


@method_decorator(admin_required, name='dispatch')
class NovoTemaView(CreateView):
    """
    View para cadastro de novo tema (tag) pelo administrador.

    Cria uma nova tag e redireciona para a listagem de temas.
    Acessível para administradores e autores-admin.
    """
    model = Tag
    template_name = 'painel_admin/novo_tema.html'
    fields = ['nome']
    success_url = reverse_lazy('painel_admin:gestao_temas')

    def get_form(self, form_class=None):
        """Customiza o formulário com classes Tailwind."""
        form = super().get_form(form_class)
        form.fields['nome'].widget.attrs.update({
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Digite o nome do tema'
        })
        form.fields['nome'].label = 'Nome do Tema'
        form.fields['nome'].help_text = 'Nome do tema/tag (ex: Crônica, Poesia, Ensaio)'
        return form

    def form_valid(self, form):
        """
        Salva o tema e redireciona com mensagem de sucesso.
        """
        self.object = form.save()

        messages.success(
            self.request,
            f'Tema "{self.object.nome}" criado com sucesso.'
        )

        return super().form_valid(form)

    def form_invalid(self, form):
        """
        Adiciona mensagem de erro se o formulário for inválido.
        """
        messages.error(
            self.request,
            'Houve um erro ao criar o tema. Por favor, corrija os erros abaixo.'
        )
        return super().form_invalid(form)


@method_decorator(admin_required, name='dispatch')
class EditarTemaView(UpdateView):
    """
    View para edição de tema (tag) existente pelo administrador.

    Permite ao admin atualizar o nome do tema.
    Acessível para administradores e autores-admin.
    """
    model = Tag
    template_name = 'painel_admin/editar_tema.html'
    fields = ['nome']
    success_url = reverse_lazy('painel_admin:gestao_temas')
    pk_url_kwarg = 'pk'

    def get_form(self, form_class=None):
        """Customiza o formulário com classes Tailwind."""
        form = super().get_form(form_class)
        form.fields['nome'].widget.attrs.update({
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Digite o nome do tema'
        })
        form.fields['nome'].label = 'Nome do Tema'
        form.fields['nome'].help_text = 'Nome do tema/tag (ex: Crônica, Poesia, Ensaio)'
        return form

    def form_valid(self, form):
        """
        Salva alterações do tema e redireciona.
        """
        self.object = form.save()

        messages.success(
            self.request,
            f'Tema "{self.object.nome}" atualizado com sucesso.'
        )

        return redirect(self.success_url)

    def form_invalid(self, form):
        """
        Adiciona mensagem de erro se o formulário for inválido.
        """
        messages.error(
            self.request,
            'Houve um erro ao atualizar o tema. Por favor, corrija os erros abaixo.'
        )
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        """
        Adiciona contexto indicando que é edição.
        """
        context = super().get_context_data(**kwargs)
        context['editando'] = True
        context['tema'] = self.object
        return context


@admin_required
def excluir_tema(request, pk):
    """
    Exclui um tema (tag) permanentemente.

    Acessível para administradores e autores-admin.
    Ao excluir, os textos associados não são deletados,
    apenas perdem a associação com este tema.

    Retorna JSON com sucesso/erro para uso com HTMX.
    """
    tema = get_object_or_404(Tag, pk=pk)

    # Contar quantos textos usam este tema
    total_textos = tema.textos.count()

    # Armazenar nome antes de deletar
    nome_tema = tema.nome

    # Deletar tema (ManyToMany não faz CASCADE, apenas remove associação)
    tema.delete()

    # Mensagem de confirmação
    if total_textos > 0:
        messages.success(
            request,
            f'Tema "{nome_tema}" foi excluído permanentemente. '
            f'{total_textos} texto(s) perderam a associação com este tema.'
        )
    else:
        messages.success(
            request,
            f'Tema "{nome_tema}" foi excluído permanentemente.'
        )

    return redirect('painel_admin:gestao_temas')


# ===============================================
# CONTATOS ADMINISTRATIVOS
# ===============================================

class ContatosAdministrativosView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    View para listar todos os contatos administrativos.

    Exibe lista com nome, e-mail, status (ativo/inativo) e data de cadastro.
    Permite criar, editar e excluir contatos.
    """
    model = ContatoAdministrativo
    template_name = 'painel_admin/contatos_administrativos.html'
    context_object_name = 'contatos'
    login_url = '/contas/login/'

    def test_func(self):
        """Verifica se o usuário pode acessar o painel administrativo."""
        return self.request.user.pode_acessar_painel_admin()


class NovoContatoAdministrativoView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """
    View para cadastrar novo contato administrativo.

    Formulário com campos: nome, e-mail e status ativo.
    """
    model = ContatoAdministrativo
    form_class = ContatoAdministrativoForm
    template_name = 'painel_admin/novo_contato.html'
    success_url = reverse_lazy('painel_admin:contatos_administrativos')
    login_url = '/contas/login/'

    def test_func(self):
        """Verifica se o usuário pode acessar o painel administrativo."""
        return self.request.user.pode_acessar_painel_admin()

    def form_valid(self, form):
        """Exibe mensagem de sucesso ao cadastrar contato."""
        messages.success(
            self.request,
            f'Contato "{form.cleaned_data["nome"]}" cadastrado com sucesso!'
        )
        return super().form_valid(form)


class EditarContatoAdministrativoView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    View para editar contato administrativo existente.

    Permite atualizar nome, e-mail e status ativo.
    """
    model = ContatoAdministrativo
    form_class = ContatoAdministrativoForm
    template_name = 'painel_admin/editar_contato.html'
    success_url = reverse_lazy('painel_admin:contatos_administrativos')
    login_url = '/contas/login/'

    def test_func(self):
        """Verifica se o usuário pode acessar o painel administrativo."""
        return self.request.user.pode_acessar_painel_admin()

    def form_valid(self, form):
        """Exibe mensagem de sucesso ao editar contato."""
        messages.success(
            self.request,
            f'Contato "{form.cleaned_data["nome"]}" atualizado com sucesso!'
        )
        return super().form_valid(form)


@login_required(login_url='/contas/login/')
def excluir_contato_administrativo(request, pk):
    """
    View para excluir um contato administrativo.

    Apenas POST é permitido. Redireciona para a listagem de contatos.
    """
    # Verificar se usuário tem permissão
    if not request.user.pode_acessar_painel_admin():
        messages.error(request, 'Você não tem permissão para acessar esta página.')
        return redirect('core:home')

    # Verificar se método é POST
    if request.method != 'POST':
        messages.error(request, 'Método não permitido.')
        return redirect('painel_admin:contatos_administrativos')

    # Buscar contato
    contato = get_object_or_404(ContatoAdministrativo, pk=pk)
    nome_contato = contato.nome

    # Excluir contato
    contato.delete()

    # Mensagem de confirmação
    messages.success(
        request,
        f'Contato "{nome_contato}" foi excluído permanentemente.'
    )

    return redirect('painel_admin:contatos_administrativos')


# ========================================
# GESTÃO DE TEMAS DE LEITURA (CRUD)
# ========================================

class TemasLeituraListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    View para listagem de Temas de Leitura (CRUD).

    Exibe todos os temas cadastrados no sistema.
    Apenas usuários admin podem acessar esta view.
    """
    from apps.core.models import TemaLeitura
    model = TemaLeitura
    template_name = 'painel_admin/temas_leitura.html'
    context_object_name = 'temas'
    ordering = ['ordem', 'nome_exibicao']

    def test_func(self):
        """Apenas admins (ADMIN ou AUTOR-ADMIN) podem acessar."""
        return self.request.user.pode_acessar_painel_admin()


class NovoTemaLeituraView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """
    View para cadastro de novo Tema de Leitura.

    Permite criar novos temas CSS customizáveis.
    Apenas usuários admin podem acessar esta view.
    """
    from apps.core.models import TemaLeitura
    model = TemaLeitura
    from .forms import TemaLeituraForm
    form_class = TemaLeituraForm
    template_name = 'painel_admin/novo_tema_leitura.html'
    success_url = reverse_lazy('painel_admin:temas_leitura')

    def test_func(self):
        """Apenas admins (ADMIN ou AUTOR-ADMIN) podem acessar."""
        return self.request.user.pode_acessar_painel_admin()

    def get_initial(self):
        """
        Define valores iniciais do formulário.

        Ordem padrão: último tema + 1 (se último está em ordem 6, novo vem em 7).
        """
        from apps.core.models import TemaLeitura

        initial = super().get_initial()

        # Buscar a maior ordem atual
        ultima_ordem = TemaLeitura.objects.aggregate(models.Max('ordem'))['ordem__max']

        # Se houver temas, próxima ordem = última + 1, senão ordem = 1
        initial['ordem'] = (ultima_ordem + 1) if ultima_ordem is not None else 1

        return initial

    def form_valid(self, form):
        """
        Processa upload do arquivo CSS e salva o tema.
        """
        import os
        from django.conf import settings

        # Verificar se há arquivo CSS enviado
        arquivo_css = self.request.FILES.get('arquivo_css')

        if arquivo_css:
            # Gerar nome do arquivo baseado no slug
            slug = form.cleaned_data['slug']
            nome_arquivo = f"{slug}.css"

            # Caminho completo onde o arquivo será salvo
            caminho_completo = os.path.join(
                settings.BASE_DIR,
                'static',
                'css',
                'themes',
                nome_arquivo
            )

            # Criar diretório se não existir
            os.makedirs(os.path.dirname(caminho_completo), exist_ok=True)

            # Salvar arquivo
            with open(caminho_completo, 'wb+') as destino:
                for chunk in arquivo_css.chunks():
                    destino.write(chunk)

            # Atualizar o campo arquivo_css do formulário
            form.instance.arquivo_css = nome_arquivo

        # Exibir mensagem de sucesso
        messages.success(
            self.request,
            f'Tema "{form.instance.nome_exibicao}" foi cadastrado com sucesso!'
        )

        return super().form_valid(form)


class EditarTemaLeituraView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    View para edição de Tema de Leitura existente.

    Permite editar dados de temas já cadastrados.
    Apenas usuários admin podem acessar esta view.
    """
    from apps.core.models import TemaLeitura
    model = TemaLeitura
    from .forms import TemaLeituraForm
    form_class = TemaLeituraForm
    template_name = 'painel_admin/editar_tema_leitura.html'
    success_url = reverse_lazy('painel_admin:temas_leitura')

    def test_func(self):
        """Apenas admins (ADMIN ou AUTOR-ADMIN) podem acessar."""
        return self.request.user.pode_acessar_painel_admin()

    def form_valid(self, form):
        """
        Processa upload do arquivo CSS (se houver) e reorganiza ordem dos temas.
        """
        import os
        from django.conf import settings
        from apps.core.models import TemaLeitura

        # 1. UPLOAD DO ARQUIVO CSS (se houver novo arquivo)
        arquivo_css = self.request.FILES.get('arquivo_css')

        if arquivo_css:
            # Gerar nome do arquivo baseado no slug
            slug = form.cleaned_data['slug']
            nome_arquivo = f"{slug}.css"

            # Caminho completo onde o arquivo será salvo
            caminho_completo = os.path.join(
                settings.BASE_DIR,
                'static',
                'css',
                'themes',
                nome_arquivo
            )

            # Criar diretório se não existir
            os.makedirs(os.path.dirname(caminho_completo), exist_ok=True)

            # Salvar arquivo
            with open(caminho_completo, 'wb+') as destino:
                for chunk in arquivo_css.chunks():
                    destino.write(chunk)

            # Atualizar o campo arquivo_css do formulário
            form.instance.arquivo_css = nome_arquivo
        else:
            # IMPORTANTE: Se não houver upload, preservar o arquivo_css atual
            # Isso evita que o campo seja limpo ao editar sem fazer novo upload
            # NOTA: Esta proteção é redundante pois clean_arquivo_css() já faz isso,
            # mas mantemos como camada extra de segurança
            form.instance.arquivo_css = self.object.arquivo_css

        # 2. REORGANIZAR ORDEM DOS TEMAS (se a ordem mudou)
        # Ordem antiga (antes da edição)
        ordem_antiga = self.object.ordem

        # Ordem nova (do formulário)
        ordem_nova = form.cleaned_data['ordem']

        # Se a ordem mudou, reorganizar
        if ordem_antiga != ordem_nova:
            if ordem_antiga < ordem_nova:
                # Movendo para baixo (ex: 2 → 4)
                # Temas entre 3 e 4 diminuem 1 (3→2, 4→3)
                TemaLeitura.objects.filter(
                    ordem__gt=ordem_antiga,
                    ordem__lte=ordem_nova
                ).exclude(pk=self.object.pk).update(ordem=F('ordem') - 1)
            else:
                # Movendo para cima (ex: 4 → 2)
                # Temas entre 2 e 3 aumentam 1 (2→3, 3→4)
                TemaLeitura.objects.filter(
                    ordem__gte=ordem_nova,
                    ordem__lt=ordem_antiga
                ).exclude(pk=self.object.pk).update(ordem=F('ordem') + 1)

        # 3. EXIBIR MENSAGEM DE SUCESSO
        messages.success(
            self.request,
            f'Tema "{form.instance.nome_exibicao}" foi atualizado com sucesso!'
        )

        return super().form_valid(form)


@login_required
def excluir_tema_leitura(request, pk):
    """
    View para exclusão de Tema de Leitura.

    Exclui permanentemente um tema do sistema.
    Apenas usuários admin (ADMIN ou AUTOR-ADMIN) podem acessar.
    O tema "padrão" não pode ser deletado (proteção no modelo).
    """
    from apps.core.models import TemaLeitura

    # Verificar se usuário pode acessar
    if not request.user.pode_acessar_painel_admin():
        messages.error(
            request,
            'Você não tem permissão para acessar esta página.'
        )
        return redirect('core:home')

    # Buscar tema
    tema = get_object_or_404(TemaLeitura, pk=pk)
    nome_tema = tema.nome_exibicao
    slug_tema = tema.slug
    ordem_deletada = tema.ordem  # Salvar ordem antes de deletar
    arquivo_css = tema.arquivo_css  # Salvar nome do arquivo CSS

    # Tentar excluir (pode falhar se for o tema padrão)
    try:
        # 1. Deletar tema do banco de dados
        tema.delete()

        # 2. Deletar arquivo CSS físico (se existir)
        if arquivo_css:
            import os
            from django.conf import settings

            caminho_arquivo = os.path.join(settings.BASE_DIR, 'static', 'css', 'themes', arquivo_css)

            if os.path.exists(caminho_arquivo):
                try:
                    os.remove(caminho_arquivo)
                except Exception as e_file:
                    # Log do erro mas não interrompe o fluxo (tema já foi deletado do banco)
                    print(f'Aviso: Erro ao deletar arquivo CSS {arquivo_css}: {e_file}')

        # 3. Reorganizar ordens: todos os temas com ordem > ordem_deletada diminuem 1
        # Exemplo: Se deletar ordem 3, então ordem 4→3, ordem 5→4, etc.
        TemaLeitura.objects.filter(ordem__gt=ordem_deletada).update(ordem=F('ordem') - 1)

        messages.success(
            request,
            f'Tema "{nome_tema}" foi excluído permanentemente (banco + arquivo CSS) e as ordens foram reorganizadas.'
        )
    except Exception as e:
        # Se for ProtectedError (tema padrão), exibir mensagem personalizada
        if 'padrão' in str(e).lower() or slug_tema == 'padrao':
            messages.error(
                request,
                f'O tema "{nome_tema}" não pode ser deletado pois é usado como padrão do sistema.'
            )
        else:
            messages.error(
                request,
                f'Erro ao excluir tema "{nome_tema}": {str(e)}'
            )

    return redirect('painel_admin:temas_leitura')


@admin_required
def configuracao_convites_view(request):
    """
    View para configuração do limite de convites por autor.

    Permite ao administrador definir quantos autores cada autor pode convidar.
    Também mostra estatísticas sobre convites utilizados.
    """
    from .models import ConfiguracaoSistema, ConviteAutor

    # Obter configuração atual
    config = ConfiguracaoSistema.get_config()

    if request.method == 'POST':
        try:
            novo_limite = int(request.POST.get('limite_convites', 5))
            if novo_limite < 0:
                novo_limite = 0
            elif novo_limite > 100:
                novo_limite = 100  # Limite máximo razoável

            config.limite_convites_autor = novo_limite
            config.save()

            messages.success(
                request,
                f'Limite de convites atualizado para {novo_limite} por autor.'
            )
        except (ValueError, TypeError):
            messages.error(
                request,
                'Valor inválido para limite de convites.'
            )

        return redirect('painel_admin:configuracao_convites')

    # Estatísticas de convites
    # Total de convites ativados (autores que aceitaram convite de outros autores)
    convites_ativados = ConviteAutor.objects.filter(
        convidado_por__isnull=False,
        ativado=True
    ).count()

    # Autores que mais convidaram
    from django.db.models import Count

    autores_top_convites = User.objects.filter(
        role=User.Role.AUTOR,
        convites_enviados__ativado=True
    ).annotate(
        total_convites=Count('convites_enviados', filter=Q(convites_enviados__ativado=True))
    ).filter(
        total_convites__gt=0
    ).order_by('-total_convites')[:10]

    context = {
        'config': config,
        'convites_ativados': convites_ativados,
        'autores_top_convites': autores_top_convites,
    }

    return render(request, 'painel_admin/configuracao_convites.html', context)


# ========================================
# GESTÃO DE AUTORES CLÁSSICOS
# ========================================

@admin_required
def gestao_autores_classicos_view(request):
    """
    View para configuração de autores clássicos.

    Permite ao administrador:
    - Definir senha padrão para todos os autores clássicos
    - Permitir/bloquear login de autores clássicos
    - Visualizar lista de autores clássicos cadastrados
    """
    from .models import ConfiguracaoSistema
    from .forms import GestaoAutoresClassicosForm

    # Obter configuração atual
    config = ConfiguracaoSistema.get_config()

    # Buscar autores clássicos com contagem de obras
    autores_classicos = User.objects.filter(
        role=User.Role.AUTOR,
        is_classico=True
    ).annotate(
        total_obras=Count('textos', filter=Q(textos__status='PUBLICADO'))
    ).order_by('first_name', 'last_name')

    total_autores_classicos = autores_classicos.count()

    if request.method == 'POST':
        form = GestaoAutoresClassicosForm(request.POST, config=config)

        if form.is_valid():
            form.save()

            # Verificar se senha foi alterada
            if form.cleaned_data['senha_autores_classicos']:
                messages.success(
                    request,
                    f'Configurações salvas! Senha atualizada para {total_autores_classicos} autor(es) clássico(s).'
                )
            else:
                messages.success(
                    request,
                    'Configurações salvas com sucesso!'
                )

            return redirect('painel_admin:gestao_autores_classicos')
    else:
        form = GestaoAutoresClassicosForm(config=config)

    context = {
        'form': form,
        'config': config,
        'autores_classicos': autores_classicos,
        'total_autores_classicos': total_autores_classicos,
    }

    return render(request, 'painel_admin/gestao_autores_classicos.html', context)


# ========================================
# COMUNICAÇÃO GERAL (E-MAIL MARKETING)
# ========================================

def obter_destinatarios_comunicacao(tipo, filtro_sexo=None, filtro_idade_min=None,
                                     filtro_idade_max=None, filtro_segue_autores=None,
                                     filtro_tempo_leitura=None):
    """
    Retorna queryset de usuários elegíveis para receber a comunicação.

    Regras base:
    - Não suspensos (is_suspended=False)
    - Não são autores clássicos (role=AUTOR e is_classico=True)
    - Têm preferências de e-mail habilitadas conforme o tipo

    Args:
        tipo: 'NOVIDADE', 'PARCEIROS' ou 'AMBOS'
        filtro_sexo: 'F', 'M', 'O' ou None (todos)
        filtro_idade_min: int ou None
        filtro_idade_max: int ou None
        filtro_segue_autores: queryset de autores ou None
        filtro_tempo_leitura: 'POUCO', 'MEDIO', 'MUITO' ou None

    Returns:
        QuerySet de usuários elegíveis
    """
    from apps.usuarios.models import AutorSeguido
    from apps.textos.models import Visualizacao
    from datetime import date

    # Base: não suspensos e excluir autores clássicos
    usuarios = User.objects.filter(
        is_suspended=False,
        is_active=True
    ).exclude(
        role=User.Role.AUTOR,
        is_classico=True
    )

    # Filtrar por preferências de e-mail conforme o tipo
    if tipo == 'NOVIDADE':
        usuarios = usuarios.filter(configuracao__receber_email_promocional=True)
    elif tipo == 'PARCEIROS':
        usuarios = usuarios.filter(configuracao__receber_email_parceiros=True)
    elif tipo == 'AMBOS':
        # Usuários que aceitam pelo menos um dos tipos
        usuarios = usuarios.filter(
            Q(configuracao__receber_email_promocional=True) |
            Q(configuracao__receber_email_parceiros=True)
        )

    # Filtro por sexo
    if filtro_sexo:
        usuarios = usuarios.filter(sexo=filtro_sexo)

    # Filtro por idade
    if filtro_idade_min or filtro_idade_max:
        hoje = date.today()

        if filtro_idade_min:
            # Data de nascimento máxima para ter idade mínima
            data_max = date(hoje.year - filtro_idade_min, hoje.month, hoje.day)
            usuarios = usuarios.filter(data_nascimento__lte=data_max)

        if filtro_idade_max:
            # Data de nascimento mínima para ter idade máxima
            data_min = date(hoje.year - filtro_idade_max - 1, hoje.month, hoje.day)
            usuarios = usuarios.filter(data_nascimento__gte=data_min)

    # Filtro por autores seguidos
    if filtro_segue_autores and filtro_segue_autores.exists():
        seguidores_ids = AutorSeguido.objects.filter(
            autor__in=filtro_segue_autores
        ).values_list('seguidor_id', flat=True).distinct()
        usuarios = usuarios.filter(id__in=seguidores_ids)

    # Filtro por tempo de leitura
    if filtro_tempo_leitura:
        # Anotar tempo total de leitura
        usuarios = usuarios.annotate(
            tempo_total=Sum('visualizacoes__tempo_permanencia')
        )

        if filtro_tempo_leitura == 'POUCO':
            # Menos de 1 hora (3600 segundos)
            usuarios = usuarios.filter(
                Q(tempo_total__lt=3600) | Q(tempo_total__isnull=True)
            )
        elif filtro_tempo_leitura == 'MEDIO':
            # Entre 1 e 10 horas (3600 a 36000 segundos)
            usuarios = usuarios.filter(tempo_total__gte=3600, tempo_total__lte=36000)
        elif filtro_tempo_leitura == 'MUITO':
            # Mais de 10 horas (36000 segundos)
            usuarios = usuarios.filter(tempo_total__gt=36000)

    return usuarios.distinct()


@admin_required
def comunicacao_geral_lista_view(request):
    """
    Lista todas as comunicações enviadas com estatísticas.
    """
    from django.conf import settings
    from .models import ComunicacaoGeral

    comunicacoes = ComunicacaoGeral.objects.all().order_by('-data_criacao')

    context = {
        'comunicacoes': comunicacoes,
        'debug': settings.DEBUG,  # Para mostrar nota sobre tracking em dev
    }

    return render(request, 'painel_admin/comunicacao_geral_lista.html', context)


@admin_required
def comunicacao_geral_nova_view(request):
    """
    Formulário para criar e enviar nova comunicação.
    Aceita parâmetro 'repetir' para carregar dados de uma comunicação anterior.
    """
    from .models import ComunicacaoGeral

    if request.method == 'POST':
        # Salvar dados na sessão para preview
        titulo = request.POST.get('titulo', '')
        conteudo = request.POST.get('conteudo', '')
        tipo = request.POST.get('tipo_comunicacao', 'NOVIDADE')

        request.session['comunicacao_dados'] = {
            'titulo': titulo,
            'conteudo': conteudo,
            'tipo': tipo,
        }

        # Redirecionar para preview se veio do botão de preview
        return redirect('painel_admin:comunicacao_geral_nova')

    # Calcular contagem inicial (todos elegíveis)
    total_potencial = obter_destinatarios_comunicacao('NOVIDADE').count()

    # Buscar autores que têm pelo menos 1 seguidor (para filtrar destinatários)
    from apps.usuarios.models import AutorSeguido
    autores_com_seguidores_ids = AutorSeguido.objects.values_list('autor_id', flat=True).distinct()
    autores = User.objects.filter(
        id__in=autores_com_seguidores_ids,
        role=User.Role.AUTOR,
        is_active=True,
        is_classico=False
    ).order_by('first_name', 'last_name')

    # Obter choices de sexo do modelo User
    sexos = User.Sexo.choices

    context = {
        'total_potencial': total_potencial,
        'autores': autores,
        'sexos': sexos,
    }

    # Verificar se é para repetir uma comunicação anterior
    repetir_id = request.GET.get('repetir')
    if repetir_id:
        try:
            comunicacao_anterior = ComunicacaoGeral.objects.get(pk=repetir_id)
            context['repetir'] = {
                'titulo': comunicacao_anterior.titulo,
                'conteudo': comunicacao_anterior.conteudo,
                'tipo': comunicacao_anterior.tipo,
                'filtro_sexo': comunicacao_anterior.filtro_sexo or '',
                'filtro_idade_min': comunicacao_anterior.filtro_idade_min or 0,
                'filtro_idade_max': comunicacao_anterior.filtro_idade_max or 120,
                'filtro_tempo_leitura': comunicacao_anterior.filtro_tempo_leitura or '',
                'filtro_segue_autores_ids': list(comunicacao_anterior.filtro_segue_autores.values_list('id', flat=True)),
            }
        except ComunicacaoGeral.DoesNotExist:
            pass

    return render(request, 'painel_admin/comunicacao_geral_nova.html', context)


@admin_required
def comunicacao_geral_preview_view(request):
    """
    Gera preview do e-mail em nova aba.
    Aceita dados via POST (AJAX) ou da sessão.
    """
    if request.method == 'POST':
        # Receber dados via POST (JSON)
        try:
            import json
            data = json.loads(request.body)
            titulo = data.get('titulo', '')
            conteudo = data.get('conteudo', '')

            # Salvar na sessão para quando abrir a aba
            request.session['comunicacao_preview'] = {
                'titulo': titulo,
                'conteudo': conteudo,
            }

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    # GET - Renderizar preview com dados da sessão
    dados = request.session.get('comunicacao_preview', {})

    if not dados:
        return HttpResponse('''
            <html>
            <head><title>Erro - LIVRE DIA</title></head>
            <body style="font-family: Georgia, serif; text-align: center; padding: 50px;">
                <h2>Nenhuma comunicação para visualizar.</h2>
                <p>Preencha o formulário e clique em "Pré-visualizar" novamente.</p>
                <button onclick="window.close()" style="padding: 10px 20px; cursor: pointer;">Fechar</button>
            </body>
            </html>
        ''')

    context = {
        'titulo': dados.get('titulo', ''),
        'conteudo': dados.get('conteudo', ''),
        'preview': True,
    }

    return render(request, 'emails/comunicacao_geral.html', context)


@admin_required
def comunicacao_geral_contar_view(request):
    """
    API para contar destinatários baseado nos filtros (AJAX).
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)

    import json
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    tipo = data.get('tipo', 'AMBOS')
    filtro_sexo = data.get('filtro_sexo') or None
    filtro_idade_min = data.get('filtro_idade_min')
    filtro_idade_max = data.get('filtro_idade_max')
    filtro_segue_autores_ids = data.get('filtro_segue_autores', [])
    filtro_tempo_leitura = data.get('filtro_tempo_leitura') or None

    # Converter IDs de autores para queryset
    filtro_segue_autores = None
    if filtro_segue_autores_ids:
        filtro_segue_autores = User.objects.filter(id__in=filtro_segue_autores_ids)

    destinatarios = obter_destinatarios_comunicacao(
        tipo=tipo,
        filtro_sexo=filtro_sexo,
        filtro_idade_min=int(filtro_idade_min) if filtro_idade_min else None,
        filtro_idade_max=int(filtro_idade_max) if filtro_idade_max else None,
        filtro_segue_autores=filtro_segue_autores,
        filtro_tempo_leitura=filtro_tempo_leitura,
    )

    return JsonResponse({
        'total': destinatarios.count(),
    })


@admin_required
def comunicacao_geral_enviar_teste_view(request):
    """
    Envia e-mail de teste para o admin logado.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)

    import json
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.conf import settings

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    titulo = data.get('titulo', 'Teste de Comunicação')
    conteudo = data.get('conteudo', '')

    # Gerar HTML do e-mail
    html_content = render_to_string('emails/comunicacao_geral.html', {
        'titulo': titulo,
        'conteudo': conteudo,
        'usuario': request.user,
        'preview': False,
        'tracking_url': '',  # Sem tracking no teste
    })

    try:
        send_mail(
            subject=f'[TESTE] {titulo}',
            message='',  # Versão texto vazia, usamos HTML
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[request.user.email],
            html_message=html_content,
            fail_silently=False,
        )

        return JsonResponse({
            'success': True,
            'message': f'E-mail de teste enviado para {request.user.email}',
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro ao enviar e-mail: {str(e)}',
        }, status=500)


@admin_required
def comunicacao_geral_enviar_view(request):
    """
    Envia a comunicação para todos os destinatários (assíncrono).
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)

    import json
    import threading
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.conf import settings
    from .models import ComunicacaoGeral, AberturaEmail

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    titulo = data.get('titulo', '')
    conteudo = data.get('conteudo', '')
    tipo = data.get('tipo', 'AMBOS')
    filtro_sexo = data.get('filtro_sexo') or None
    filtro_idade_min = data.get('filtro_idade_min')
    filtro_idade_max = data.get('filtro_idade_max')
    filtro_segue_autores_ids = data.get('filtro_segue_autores', [])
    filtro_tempo_leitura = data.get('filtro_tempo_leitura') or None

    # Converter IDs de autores para queryset
    filtro_segue_autores = None
    if filtro_segue_autores_ids:
        filtro_segue_autores = User.objects.filter(id__in=filtro_segue_autores_ids)

    # Obter destinatários
    destinatarios = obter_destinatarios_comunicacao(
        tipo=tipo,
        filtro_sexo=filtro_sexo,
        filtro_idade_min=int(filtro_idade_min) if filtro_idade_min else None,
        filtro_idade_max=int(filtro_idade_max) if filtro_idade_max else None,
        filtro_segue_autores=filtro_segue_autores,
        filtro_tempo_leitura=filtro_tempo_leitura,
    )

    total = destinatarios.count()

    if total == 0:
        return JsonResponse({
            'success': False,
            'message': 'Nenhum destinatário encontrado com os filtros aplicados.',
        })

    # Criar registro da comunicação
    comunicacao = ComunicacaoGeral.objects.create(
        titulo=titulo,
        conteudo=conteudo,
        tipo=tipo,
        filtro_sexo=filtro_sexo,
        filtro_idade_min=int(filtro_idade_min) if filtro_idade_min else None,
        filtro_idade_max=int(filtro_idade_max) if filtro_idade_max else None,
        filtro_tempo_leitura=filtro_tempo_leitura,
        total_destinatarios=total,
        status='ENVIANDO',
        criado_por=request.user,
    )

    # Adicionar autores seguidos ao filtro (M2M)
    if filtro_segue_autores:
        comunicacao.filtro_segue_autores.set(filtro_segue_autores)

    # Função para envio em background
    def enviar_emails_background(comunicacao_id, destinatarios_ids):
        from django.db import connection
        connection.close()  # Fechar conexão da thread pai

        try:
            comunicacao = ComunicacaoGeral.objects.get(id=comunicacao_id)
            destinatarios = User.objects.filter(id__in=destinatarios_ids)

            enviados = 0
            erros = []

            for usuario in destinatarios:
                try:
                    # Criar registro de abertura com token único
                    abertura = AberturaEmail.objects.create(
                        comunicacao=comunicacao,
                        usuario=usuario,
                    )

                    # URL de tracking
                    tracking_url = f"{settings.SITE_URL}/email/tracking/{abertura.token}/"

                    # URL de configurações com token seguro
                    from apps.usuarios.views import gerar_token_email_prefs
                    email_token = gerar_token_email_prefs(usuario.id)
                    config_url = f"{settings.SITE_URL}/contas/email-prefs/{email_token}/"

                    # Gerar HTML do e-mail
                    html_content = render_to_string('emails/comunicacao_geral.html', {
                        'titulo': comunicacao.titulo,
                        'conteudo': comunicacao.conteudo,
                        'usuario': usuario,
                        'preview': False,
                        'tracking_url': tracking_url,
                        'config_url': config_url,
                    })

                    send_mail(
                        subject=comunicacao.titulo,
                        message='',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[usuario.email],
                        html_message=html_content,
                        fail_silently=False,
                    )

                    enviados += 1

                except Exception as e:
                    erros.append(f'{usuario.email}: {str(e)}')

            # Atualizar status da comunicação
            comunicacao.status = 'ENVIADO'
            comunicacao.data_envio = timezone.now()
            comunicacao.total_destinatarios = enviados

            if erros:
                comunicacao.erro_mensagem = '\n'.join(erros[:10])  # Primeiros 10 erros
                if len(erros) > 10:
                    comunicacao.erro_mensagem += f'\n... e mais {len(erros) - 10} erros'

            comunicacao.save()

        except Exception as e:
            try:
                comunicacao = ComunicacaoGeral.objects.get(id=comunicacao_id)
                comunicacao.status = 'ERRO'
                comunicacao.erro_mensagem = str(e)
                comunicacao.save()
            except:
                pass

    # Iniciar thread de envio
    destinatarios_ids = list(destinatarios.values_list('id', flat=True))
    thread = threading.Thread(
        target=enviar_emails_background,
        args=(comunicacao.id, destinatarios_ids)
    )
    thread.start()

    return JsonResponse({
        'success': True,
        'message': f'Envio iniciado para {total} destinatários. Acompanhe o progresso na lista de comunicações.',
        'comunicacao_id': comunicacao.id,
    })


@admin_required
def comunicacao_geral_detalhes_view(request, pk):
    """
    Exibe detalhes e estatísticas de uma comunicação enviada.
    """
    from .models import ComunicacaoGeral

    comunicacao = get_object_or_404(ComunicacaoGeral, pk=pk)

    # Usuários que abriram o e-mail
    aberturas = comunicacao.aberturas.filter(aberto=True).select_related('usuario')

    context = {
        'comunicacao': comunicacao,
        'aberturas': aberturas,
    }

    return render(request, 'painel_admin/comunicacao_geral_detalhes.html', context)


def email_tracking_view(request, token):
    """
    Endpoint público para registrar abertura de e-mail via pixel de tracking.

    Retorna uma imagem 1x1 pixel transparente (GIF).
    """
    from .models import AberturaEmail

    try:
        abertura = AberturaEmail.objects.get(token=token)

        if not abertura.aberto:
            abertura.aberto = True
            abertura.data_abertura = timezone.now()
            abertura.ip_address = request.META.get('REMOTE_ADDR')
            abertura.user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            abertura.save()

            # Atualizar contador na comunicação
            abertura.comunicacao.total_aberturas = abertura.comunicacao.aberturas.filter(aberto=True).count()
            abertura.comunicacao.save(update_fields=['total_aberturas'])

    except AberturaEmail.DoesNotExist:
        pass

    # Retornar GIF 1x1 pixel transparente
    gif_1x1 = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'

    return HttpResponse(gif_1x1, content_type='image/gif')


@admin_required
def comunicacao_geral_excluir_view(request, pk):
    """
    Exclui uma comunicação geral e todos os registros de abertura associados.
    Requer confirmação via POST. Suporta requisições AJAX.
    """
    from .models import ComunicacaoGeral
    from django.contrib import messages

    comunicacao = get_object_or_404(ComunicacaoGeral, pk=pk)

    if request.method == 'POST':
        titulo = comunicacao.titulo
        comunicacao.delete()

        # Verificar se é requisição AJAX
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                  'application/json' in request.headers.get('Accept', '')

        if is_ajax:
            return JsonResponse({'success': True, 'message': f'Comunicação "{titulo}" excluída com sucesso.'})

        messages.success(request, f'Comunicação "{titulo}" excluída com sucesso.')
        return redirect('painel_admin:comunicacao_geral_lista')

    # Se não for POST, redirecionar para a lista
    return redirect('painel_admin:comunicacao_geral_lista')
