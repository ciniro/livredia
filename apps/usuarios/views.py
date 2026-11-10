from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView, UpdateView, FormView, TemplateView, View, ListView
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404, render
from django.http import Http404, HttpResponse
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from .forms import LeitorCadastroForm, EditarPerfilForm, ExcluirContaForm, AlterarSenhaForm, DefinirSenhaForm, CustomAuthenticationForm
from .models import EmailConfirmationToken, PasswordResetToken, User, ConfiguracaoUsuario
from apps.textos.models import Texto, TextoFavorito, TextoLido, TextoLeituraPosterior, CartaoBiblioteca
from apps.core.models import Notificacao


class CustomLoginView(LoginView):
    """
    View de login customizada usando LoginView padrão do Django.

    Utiliza o backend EmailBackend para permitir login com email ou username.
    Template baseado no protótipo HTML em prototipos_telas/página_de_login/

    IMPORTANTE: Bloqueia login de usuários suspensos (is_suspended=True).

    Item 7 do ROADMAP: Adicionado Cloudflare Turnstile para proteção contra bots.
    """
    template_name = 'usuarios/login.html'
    authentication_form = CustomAuthenticationForm  # Com Cloudflare Turnstile (Item 7)
    redirect_authenticated_user = True  # Redireciona se já estiver autenticado

    def form_valid(self, form):
        """
        Valida o formulário de login e verifica:
        1. Se leitor confirmou e-mail (email_verified)
        2. Se usuário está suspenso (is_suspended)
        3. Se autor clássico pode fazer login (is_classico + config)

        Bloqueios aplicados nesta ordem:
        - Leitores não confirmados → redireciona para login com mensagem
        - Usuários suspensos → redireciona para login com mensagem
        - Autores clássicos bloqueados → redireciona para login com mensagem
        """
        # Obter usuário autenticado pelo form
        user = form.get_user()

        # VERIFICAÇÃO 1: E-mail não confirmado (apenas para LEITORES)
        if user.role == 'LEITOR' and not user.email_verified:
            # Bloquear login e exibir mensagem
            messages.warning(
                self.request,
                'Você precisa confirmar seu e-mail antes de fazer login. '
                'Verifique sua caixa de entrada ou clique no botão abaixo para reenviar o e-mail de confirmação.'
            )
            # Armazenar email na sessão para mostrar botão de reenvio
            self.request.session['pending_confirmation_email'] = user.email
            # Redirecionar de volta para página de login (sem fazer login)
            return redirect('usuarios:login')

        # VERIFICAÇÃO 2: Usuário suspenso
        if hasattr(user, 'is_suspended') and user.is_suspended:
            # Bloquear login e exibir mensagem
            messages.error(
                self.request,
                'Você foi suspenso pelo LIVRE DIA. Se desejar, entre em contato através do formulário em Fale Conosco.'
            )
            # Redirecionar de volta para página de login (sem fazer login)
            return redirect('usuarios:login')

        # VERIFICAÇÃO 3: Autor clássico com login bloqueado
        if hasattr(user, 'is_classico') and user.is_classico:
            from apps.painel_admin.models import ConfiguracaoSistema
            config = ConfiguracaoSistema.get_config()
            if not config.autores_classicos_podem_login:
                # Bloquear login de autores clássicos
                messages.error(
                    self.request,
                    'O acesso de autores clássicos está temporariamente desabilitado.'
                )
                return redirect('usuarios:login')

        # ETAPA 7 - Sistema de Selos: Detectar selos pendentes após login
        # Buscar todos os selos que o usuário ganhou mas ainda não visualizou o modal
        from apps.usuarios.models import AutorSeguido
        selos_pendentes = AutorSeguido.objects.filter(
            seguidor=user,
            is_leitor_especial=True,
            selo_especial_modal_exibido=False
        ).select_related('autor')

        # Armazenar IDs dos selos pendentes na sessão para exibir modals após redirect
        if selos_pendentes.exists():
            self.request.session['selos_pendentes_ids'] = list(
                selos_pendentes.values_list('id', flat=True)
            )

        # Se passou por todas as verificações, prosseguir com login normal
        return super().form_valid(form)

    def get_success_url(self):
        """
        Redireciona para a página apropriada após login bem-sucedido.

        Ordem de prioridade:
        1. Parâmetro 'next' da URL (se existir)
        2. Redirecionamento baseado no perfil do usuário:
           - ADMIN (role=ADMIN) → /painel-admin/ (Dashboard Administrativo)
           - AUTOR (role=AUTOR) → /autor/ (Dashboard do Autor)
           - LEITOR (role=LEITOR) → / (Home)
        """
        # Verificar se existe parâmetro 'next' na URL
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url

        # Caso contrário, redirecionar baseado no perfil
        user = self.request.user

        if user.is_authenticated:
            # 1. Administradores puros (ADMIN) → Área Administrativa
            if user.role == 'ADMIN':
                return reverse_lazy('painel_admin:dashboard')

            # 2. Autores (AUTOR, com ou sem is_admin) → Área do Autor
            elif user.role == 'AUTOR':
                return reverse_lazy('painel_autor:dashboard')

            # 3. Leitores (LEITOR) → Home

        # Fallback: Home
        return reverse_lazy('core:home')


class CustomLogoutView(LogoutView):
    """
    View de logout customizada usando LogoutView padrão do Django.
    Redireciona para a home após logout.
    """
    next_page = 'core:home'


class CadastroLeitorView(CreateView):
    """
    View de cadastro customizada para Leitores.

    Utiliza o LeitorCadastroForm customizado.
    Após cadastro, envia e-mail de confirmação e redireciona para tela de confirmação.

    IMPORTANTE: Não faz login automático. Login só é permitido após confirmação de e-mail.
    """
    form_class = LeitorCadastroForm
    template_name = 'usuarios/cadastro.html'
    success_url = reverse_lazy('usuarios:confirmacao_enviada')

    def form_valid(self, form):
        """
        Salva o usuário com email_verified=False, gera token e envia e-mail de confirmação.
        """
        try:
            # Salvar o usuário (email_verified=False por padrão)
            response = super().form_valid(form)

            # Verificar se já existe um token para este usuário (cleanup de segurança)
            EmailConfirmationToken.objects.filter(user=self.object).delete()

            # Gerar token de confirmação
            token = EmailConfirmationToken.objects.create(user=self.object)

            # Enviar e-mail de confirmação
            self.enviar_email_confirmacao(self.object, token)

            # Armazenar e-mail na sessão para possível reenvio
            self.request.session['pending_confirmation_email'] = self.object.email

            return response

        except Exception as e:
            # Logar erro para debug
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao processar cadastro: {str(e)}", exc_info=True)

            # Deletar usuário criado para evitar dados órfãos
            if hasattr(self, 'object') and self.object.pk:
                self.object.delete()

            # Mostrar mensagem amigável ao usuário
            messages.error(
                self.request,
                'Ocorreu um erro ao processar seu cadastro. Por favor, tente novamente. '
                'Se o problema persistir, entre em contato conosco.'
            )
            return self.form_invalid(form)

    def enviar_email_confirmacao(self, user, token):
        """
        Envia e-mail de confirmação para o usuário recém-cadastrado.
        """
        # Gerar link de confirmação
        confirmation_link = self.request.build_absolute_uri(
            reverse('usuarios:confirmar_email', kwargs={'token': token.token})
        )

        # Renderizar template de e-mail
        html_message = render_to_string('emails/confirmacao_email.html', {
            'nome': user.first_name,
            'confirmation_link': confirmation_link,
        })

        # Enviar e-mail
        send_mail(
            subject='Confirme seu e-mail no LIVRE DIA',
            message='',  # Mensagem texto plano (vazia, usamos HTML)
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

    def form_invalid(self, form):
        """
        Adiciona mensagem de erro se o formulário for inválido.
        """
        messages.error(
            self.request,
            'Houve um erro no seu cadastro. Por favor, corrija os erros abaixo.'
        )
        return super().form_invalid(form)


class MinhaContaView(LoginRequiredMixin, TemplateView):
    """
    View para edição de perfil e alteração de senha do usuário logado.
    Gerencia dois formulários na mesma página: EditarPerfilForm e AlterarSenhaForm/DefinirSenhaForm.

    Para usuários que se cadastraram via Google e não possuem senha:
    - Usa DefinirSenhaForm (não exige senha atual)

    Para usuários que já possuem senha:
    - Usa AlterarSenhaForm (exige senha atual)
    """
    template_name = 'usuarios/minha_conta.html'

    def get_senha_form_class(self):
        """
        Retorna a classe de formulário de senha apropriada.

        - DefinirSenhaForm: para usuários sem senha (ex: cadastrados via Google)
        - AlterarSenhaForm: para usuários com senha tradicional
        """
        if self.request.user.has_usable_password():
            return AlterarSenhaForm
        return DefinirSenhaForm

    def get_context_data(self, **kwargs):
        """Adiciona ambos os formulários ao contexto."""
        context = super().get_context_data(**kwargs)

        # Formulário de perfil
        if 'form' not in kwargs:
            context['form'] = EditarPerfilForm(instance=self.request.user)

        # Formulário de senha - usa classe apropriada baseada em has_usable_password()
        if 'senha_form' not in kwargs:
            SenhaFormClass = self.get_senha_form_class()
            if SenhaFormClass == AlterarSenhaForm:
                context['senha_form'] = SenhaFormClass(user=self.request.user)
            else:
                # DefinirSenhaForm não recebe user no construtor
                context['senha_form'] = SenhaFormClass()

        # Flag para o template saber se usuário tem senha ou não
        context['usuario_tem_senha'] = self.request.user.has_usable_password()

        return context

    def post(self, request, *args, **kwargs):
        """Processa o formulário enviado (perfil ou senha)."""

        # Verificar qual formulário foi enviado
        if 'alterar_perfil' in request.POST:
            return self.processar_perfil(request)
        elif 'alterar_senha' in request.POST:
            return self.processar_senha(request)

        return self.get(request, *args, **kwargs)

    def processar_perfil(self, request):
        """Processa o formulário de edição de perfil."""
        form = EditarPerfilForm(request.POST, request.FILES, instance=request.user)

        if form.is_valid():
            form.save()
            messages.success(request, 'Seu perfil foi atualizado com sucesso!')
            return redirect('usuarios:minha_conta')
        else:
            messages.error(request, 'Houve um erro ao atualizar seu perfil. Corrija os erros abaixo.')
            # Obter formulário de senha apropriado
            SenhaFormClass = self.get_senha_form_class()
            if SenhaFormClass == AlterarSenhaForm:
                senha_form = SenhaFormClass(user=request.user)
            else:
                senha_form = SenhaFormClass()
            return self.render_to_response(
                self.get_context_data(form=form, senha_form=senha_form)
            )

    def processar_senha(self, request):
        """
        Processa o formulário de alteração/definição de senha.

        Usa o formulário apropriado baseado em has_usable_password():
        - AlterarSenhaForm: para usuários com senha (exige senha atual)
        - DefinirSenhaForm: para usuários sem senha (não exige senha atual)
        """
        SenhaFormClass = self.get_senha_form_class()

        if SenhaFormClass == AlterarSenhaForm:
            # Usuário tem senha - usar AlterarSenhaForm
            senha_form = AlterarSenhaForm(user=request.user, data=request.POST)
            if senha_form.is_valid():
                user = senha_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Sua senha foi alterada com sucesso!')
                return redirect('usuarios:minha_conta')
        else:
            # Usuário não tem senha - usar DefinirSenhaForm
            senha_form = DefinirSenhaForm(data=request.POST)
            if senha_form.is_valid():
                user = senha_form.save(request.user)
                update_session_auth_hash(request, user)
                messages.success(request, 'Sua senha foi definida com sucesso! Agora você pode fazer login com email e senha.')
                return redirect('usuarios:minha_conta')

        # Se chegou aqui, o formulário é inválido
        messages.error(request, 'Houve um erro ao processar sua senha. Corrija os erros abaixo.')
        return self.render_to_response(
            self.get_context_data(form=EditarPerfilForm(instance=request.user), senha_form=senha_form)
        )


class ExcluirContaView(LoginRequiredMixin, FormView):
    """
    View para exclusão de conta do usuário.
    Requer confirmação dupla (digitar "EXCLUIR").
    Deleta CASCADE: comentários e textos (se for autor).

    Proteções especiais:
    - Superadmin (adm@gmail.com) NUNCA pode ser excluído
    - Último admin (excluindo superadmin) não pode deletar própria conta
    """
    form_class = ExcluirContaForm
    template_name = 'usuarios/excluir_conta.html'
    success_url = reverse_lazy('core:home')

    def get_context_data(self, **kwargs):
        """Adiciona informações sobre restrições de exclusão ao contexto."""
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Verificar se é superadmin
        context['is_superadmin'] = (user.email == 'adm@gmail.com')

        # Verificar se é o último admin (excluindo superadmin)
        if user.role == 'ADMIN':
            from apps.usuarios.models import User
            total_admins = User.objects.filter(role='ADMIN').exclude(email='adm@gmail.com').count()
            context['is_last_admin'] = (total_admins == 1)
        else:
            context['is_last_admin'] = False

        return context

    def form_valid(self, form):
        """
        Exclui a conta do usuário e todos os dados relacionados.
        Aplica proteções para superadmin e último admin.
        """
        user = self.request.user
        username = user.first_name

        # PROTEÇÃO 1: Superadmin NUNCA pode ser excluído
        if user.email == 'adm@gmail.com':
            messages.error(
                self.request,
                'Esta conta não pode ser excluída pois é o superadministrador do sistema.'
            )
            return redirect('usuarios:excluir_conta')

        # PROTEÇÃO 2: Último admin (excluindo superadmin) não pode deletar própria conta
        if user.role == 'ADMIN':
            from apps.usuarios.models import User
            total_admins = User.objects.filter(role='ADMIN').exclude(email='adm@gmail.com').count()
            if total_admins == 1:
                messages.error(
                    self.request,
                    'Você é o único administrador do sistema. Adicione um novo administrador antes de excluir sua conta.'
                )
                return redirect('usuarios:excluir_conta')

        # Fazer logout antes de excluir
        logout(self.request)

        # Excluir usuário (CASCADE vai deletar comentários e textos automaticamente)
        user.delete()

        messages.success(
            self.request,
            f'Sua conta foi excluída permanentemente, {username}. Sentiremos sua falta.'
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        """Adiciona mensagem de erro."""
        messages.error(self.request, 'Confirmação incorreta. Digite EXCLUIR (em maiúsculas) para confirmar.')
        return super().form_invalid(form)


class ConfirmarEmailView(View):
    """
    View para processar confirmação de e-mail via link único.

    Valida o token UUID recebido na URL, marca email_verified=True e redireciona para login.
    Tokens expiram após 7 dias.
    """

    def get(self, request, token):
        """
        Processa confirmação de e-mail.

        Args:
            token (UUID): Token único de confirmação

        Returns:
            Redirect: Para login com mensagem de sucesso/erro
        """
        # Buscar token no banco de dados
        token_obj = get_object_or_404(EmailConfirmationToken, token=token)

        # Verificar se token expirou
        if token_obj.is_expired():
            messages.error(
                request,
                'Este link de confirmação expirou (válido por 7 dias). '
                'Clique no botão abaixo para receber um novo e-mail de confirmação.'
            )
            # Armazenar e-mail para reenvio
            request.session['pending_confirmation_email'] = token_obj.user.email
            return redirect('usuarios:login')

        # Token válido: confirmar e-mail
        user = token_obj.user
        user.email_verified = True
        user.save()

        # Deletar token usado (não pode ser reutilizado)
        token_obj.delete()

        # Limpar sessão de email pendente
        if 'pending_confirmation_email' in request.session:
            del request.session['pending_confirmation_email']

        # Armazenar flag de confirmação bem-sucedida e email na sessão
        request.session['email_just_confirmed'] = True
        request.session['confirmed_email'] = user.email
        request.session['confirmed_user_name'] = user.first_name

        # Redirecionar para página de confirmação (mostrará mensagem de sucesso)
        return redirect('usuarios:confirmacao_enviada')


class ConfirmacaoEnviadaView(TemplateView):
    """
    Tela exibida após cadastro informando que e-mail de confirmação foi enviado.

    Mostra instruções para verificar caixa de entrada e oferece opção de reenvio.
    Se o usuário já confirmou o email, exibe mensagem de sucesso com link para home.
    """
    template_name = 'usuarios/confirmacao_enviada.html'

    def get_context_data(self, **kwargs):
        """Adiciona e-mail e status de verificação ao contexto."""
        context = super().get_context_data(**kwargs)

        # Verificar se email acabou de ser confirmado (via sessão)
        if self.request.session.get('email_just_confirmed', False):
            context['email_confirmado'] = True
            context['email'] = self.request.session.get('confirmed_email', '')
            context['user_name'] = self.request.session.get('confirmed_user_name', '')
            # Limpar flags da sessão após usar
            del self.request.session['email_just_confirmed']
            if 'confirmed_email' in self.request.session:
                del self.request.session['confirmed_email']
            if 'confirmed_user_name' in self.request.session:
                del self.request.session['confirmed_user_name']
        # Verificar se usuário está autenticado e já confirmou email
        elif self.request.user.is_authenticated:
            context['email_confirmado'] = self.request.user.email_verified
            context['email'] = self.request.user.email
            context['user_name'] = self.request.user.first_name
        # Email pendente de confirmação
        else:
            context['email_confirmado'] = False
            context['email'] = self.request.session.get('pending_confirmation_email', '')
            context['user_name'] = ''

        return context


class ReenviarConfirmacaoView(View):
    """
    View para reenviar e-mail de confirmação.

    Não exige autenticação nem validação de senha/recaptcha.
    Apenas solicita o e-mail e reenvia o link de confirmação.
    """

    def get(self, request):
        """
        Mostra formulário simples para solicitar reenvio.
        """
        # Obter email da sessão (se existir) para pré-preencher
        email = request.session.get('pending_confirmation_email', '')
        return render(request, 'usuarios/reenviar_confirmacao.html', {'email': email})

    def post(self, request):
        """
        Reenvia e-mail de confirmação para o email fornecido.

        Não exige validação de senha ou recaptcha.
        Apenas verifica se email existe e não está confirmado.

        Returns:
            Redirect: Para tela de confirmação enviada
        """
        # Obter e-mail do formulário
        email = request.POST.get('email', '').strip().lower()

        if not email:
            messages.error(request, 'Por favor, informe seu e-mail.')
            return redirect('usuarios:reenviar_confirmacao')

        # Buscar usuário com email não confirmado
        try:
            from .models import User
            user = User.objects.get(email=email, role='LEITOR', email_verified=False)
        except User.DoesNotExist:
            # Por segurança, não informamos se o email existe ou não
            # Sempre mostramos mensagem de sucesso para evitar enumeração de usuários
            messages.success(
                request,
                f'Se o e-mail {email} estiver cadastrado e pendente de confirmação, '
                'você receberá um novo link de confirmação. Verifique sua caixa de entrada e spam.'
            )
            # Armazenar email na sessão
            request.session['pending_confirmation_email'] = email
            return redirect('usuarios:confirmacao_enviada')

        # Deletar token antigo se existir
        EmailConfirmationToken.objects.filter(user=user).delete()

        # Criar novo token
        token = EmailConfirmationToken.objects.create(user=user)

        # Reenviar e-mail
        self.enviar_email_confirmacao(request, user, token)

        # Armazenar email na sessão
        request.session['pending_confirmation_email'] = user.email

        # Mensagem de sucesso
        messages.success(
            request,
            f'E-mail de confirmação reenviado para {user.email}. Verifique sua caixa de entrada e spam.'
        )

        return redirect('usuarios:confirmacao_enviada')

    def enviar_email_confirmacao(self, request, user, token):
        """
        Envia e-mail de confirmação.

        Args:
            request: HttpRequest object
            user: User object
            token: EmailConfirmationToken object
        """
        # Gerar link de confirmação
        confirmation_link = request.build_absolute_uri(
            reverse('usuarios:confirmar_email', kwargs={'token': token.token})
        )

        # Renderizar template de e-mail
        html_message = render_to_string('emails/confirmacao_email.html', {
            'nome': user.first_name,
            'confirmation_link': confirmation_link,
        })

        # Enviar e-mail
        send_mail(
            subject='Confirme seu e-mail no LIVRE DIA',
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )


class SolicitarRecuperacaoView(View):
    """
    View para solicitar recuperação de senha.

    Item 14 do ROADMAP: Sistema de recuperação de senha via e-mail.

    Fluxo:
    1. Usuário informa e-mail
    2. Sistema valida:
       - LEITOR: deve ter e-mail confirmado (email_verified=True)
       - AUTOR: deve estar ativo (is_active=True)
    3. Se válido: cria token e envia e-mail
    4. Mensagem genérica sempre (não revela se e-mail existe)
    """
    template_name = 'usuarios/solicitar_recuperacao.html'

    def get(self, request):
        """Exibe formulário de solicitação"""
        return redirect('usuarios:solicitar_recuperacao') if request.user.is_authenticated else self.render_form(request)

    def post(self, request):
        """Processa solicitação de recuperação"""
        email = request.POST.get('email', '').strip()

        if not email:
            messages.error(request, 'Por favor, informe seu e-mail.')
            return self.render_form(request, email)

        # Buscar usuário pelo e-mail
        try:
            user = User.objects.get(email=email)

            # Validação: LEITOR deve ter e-mail confirmado
            if user.role == 'LEITOR' and not user.email_verified:
                # Não revelar que e-mail existe - mensagem genérica
                return self.show_success_message(request)

            # Validação: AUTOR deve estar ativo
            if user.role == 'AUTOR' and not user.is_active:
                # Não revelar que e-mail existe - mensagem genérica
                return self.show_success_message(request)

            # Usuário válido: deletar token antigo e criar novo
            PasswordResetToken.objects.filter(user=user).delete()
            token = PasswordResetToken.objects.create(user=user)

            # Enviar e-mail
            self.enviar_email_recuperacao(request, user, token)

        except User.DoesNotExist:
            # E-mail não existe - mas retorna mensagem genérica (segurança)
            pass

        # Sempre retorna mensagem genérica (não revela se e-mail existe)
        return self.show_success_message(request)

    def render_form(self, request, email=''):
        """Renderiza formulário de solicitação"""
        from django.shortcuts import render
        return render(request, self.template_name, {'email': email})

    def show_success_message(self, request):
        """Exibe mensagem genérica de sucesso"""
        messages.success(
            request,
            'Se este e-mail estiver cadastrado no sistema, você receberá instruções para redefinir sua senha. '
            'Verifique sua caixa de entrada e spam.'
        )
        return redirect('usuarios:login')

    def enviar_email_recuperacao(self, request, user, token):
        """
        Envia e-mail de recuperação.

        Args:
            request: HttpRequest object
            user: User object
            token: PasswordResetToken object
        """
        # Gerar link de redefinição
        reset_link = request.build_absolute_uri(
            reverse('usuarios:redefinir_senha', kwargs={'token': token.token})
        )

        # Renderizar template de e-mail
        html_message = render_to_string('emails/recuperacao_senha.html', {
            'nome': user.first_name,
            'reset_link': reset_link,
        })

        # Enviar e-mail
        send_mail(
            subject='Recupere sua senha no LIVRE DIA',
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )


class RedefinirSenhaView(View):
    """
    View para redefinir senha usando token.

    Item 14 do ROADMAP: Sistema de recuperação de senha via e-mail.

    Fluxo:
    1. Usuário acessa link com token UUID
    2. Sistema valida token (existe? expirou?)
    3. Usuário define nova senha
    4. Token é deletado após sucesso
    """
    template_name = 'usuarios/redefinir_senha.html'

    def get(self, request, token):
        """Exibe formulário de redefinição se token válido"""
        # Validar token
        token_obj = self.validar_token(request, token)
        if not token_obj:
            return redirect('usuarios:login')

        # Token válido: exibir formulário
        from django.shortcuts import render
        return render(request, self.template_name)

    def post(self, request, token):
        """Processa redefinição de senha"""
        # Validar token
        token_obj = self.validar_token(request, token)
        if not token_obj:
            return redirect('usuarios:login')

        # Obter senhas do formulário
        password1 = request.POST.get('password1', '').strip()
        password2 = request.POST.get('password2', '').strip()

        # Validar senhas
        if not password1 or not password2:
            messages.error(request, 'Por favor, preencha todos os campos.')
            from django.shortcuts import render
            return render(request, self.template_name)

        if password1 != password2:
            messages.error(request, 'As senhas não conferem. Por favor, tente novamente.')
            from django.shortcuts import render
            return render(request, self.template_name)

        # Redefinir senha
        user = token_obj.user
        user.set_password(password1)
        user.save()

        # Deletar token (uso único)
        token_obj.delete()

        # Mensagem de sucesso
        messages.success(
            request,
            'Senha redefinida com sucesso! Faça login com sua nova senha.'
        )

        return redirect('usuarios:login')

    def validar_token(self, request, token):
        """
        Valida token de recuperação.

        Returns:
            PasswordResetToken object se válido, None se inválido/expirado
        """
        try:
            token_obj = PasswordResetToken.objects.get(token=token)

            # Verificar se expirou (24 horas)
            if token_obj.is_expired():
                messages.error(
                    request,
                    'Link de recuperação expirado. Por favor, solicite um novo link.'
                )
                token_obj.delete()  # Deletar token expirado
                return None

            return token_obj

        except PasswordResetToken.DoesNotExist:
            messages.error(
                request,
                'Link de recuperação inválido ou já utilizado.'
            )
            return None


def verificar_username_disponivel(request):
    """
    Endpoint AJAX para verificar se um username está disponível.

    Valida:
    - Formato do username (apenas a-z, 0-9, -, _)
    - Tamanho (3-30 caracteres)
    - Não começa/termina com hífen ou sublinhado
    - Unicidade no banco de dados

    Retorna JSON com:
    - available: bool (se está disponível)
    - message: str (mensagem descritiva)
    """
    import re
    from django.http import JsonResponse

    username = request.GET.get('username', '').lower().strip()

    # Validar se username foi fornecido
    if not username:
        return JsonResponse({
            'available': False,
            'message': 'Digite um ID de usuário.'
        })

    # Validar tamanho mínimo
    if len(username) < 3:
        return JsonResponse({
            'available': False,
            'message': 'Mínimo 3 caracteres.'
        })

    # Validar tamanho máximo
    if len(username) > 30:
        return JsonResponse({
            'available': False,
            'message': 'Máximo 30 caracteres.'
        })

    # Validar formato (apenas a-z, 0-9, -, _)
    if not re.match(r'^[a-z0-9_-]+$', username):
        return JsonResponse({
            'available': False,
            'message': 'Use apenas letras minúsculas, números, - ou _.'
        })

    # Validar se não começa ou termina com hífen ou sublinhado
    if username[0] in ['-', '_'] or username[-1] in ['-', '_']:
        return JsonResponse({
            'available': False,
            'message': 'Não pode começar ou terminar com - ou _.'
        })

    # Validar unicidade
    if User.objects.filter(username=username).exists():
        return JsonResponse({
            'available': False,
            'message': 'Este @ já está em uso.'
        })

    # Username disponível!
    return JsonResponse({
        'available': True,
        'message': 'Disponível!'
    })


class PerfilPublicoView(TemplateView):
    """
    View para exibir página pública de perfil de usuário (Item 5.3 do ROADMAP).

    Acessível via URL: /@username (ex: /@ciniro)

    Funcionalidades:
    - Páginas públicas (não precisa login)
    - 2 templates: perfil_autor.html (para autores) e perfil_leitor.html (demais roles)
    - Suporte a perfis privados (exibe mensagem se perfil_privado=True)
    - Redireciona para home se usuário não encontrado

    Conteúdo exibido (Item 5.3):
    - Nome do usuário
    - ID do usuário (@username)
    - Role (badge colorido)
    - Desde quando está cadastrado
    - Foto de perfil
    """

    def get_template_names(self):
        """
        Escolhe template baseado no role do usuário.
        - AUTOR ou AUTOR_ADMIN → perfil_autor.html
        - LEITOR ou ADMIN → perfil_leitor.html
        """
        user = self.get_user()
        if user and user.role in ['AUTOR', 'AUTOR_ADMIN']:
            return ['usuarios/perfil_autor.html']
        return ['usuarios/perfil_leitor.html']

    def get_user(self):
        """
        Busca usuário pelo username da URL.
        Armazena em self.user_profile para reutilização.
        """
        if not hasattr(self, 'user_profile'):
            username = self.kwargs.get('username')
            try:
                self.user_profile = User.objects.get(username=username)
            except User.DoesNotExist:
                self.user_profile = None
        return self.user_profile

    def get(self, request, *args, **kwargs):
        """
        Processa requisição GET.
        - Se usuário não encontrado → redireciona para home
        - Se encontrado → renderiza template apropriado
        - Se requisição HTMX (SEÇÃO b) → retorna apenas fragmento da lista de textos
        """
        user = self.get_user()

        # Se usuário não existe, redireciona para home
        if not user:
            return redirect('core:home')

        # Se é requisição HTMX (filtro da SEÇÃO b), retornar apenas o fragmento
        if request.headers.get('HX-Request') and user.role in ['AUTOR', 'AUTOR_ADMIN']:
            from django.template.loader import render_to_string
            context = self.get_context_data(**kwargs)
            html = render_to_string('usuarios/partials/perfil_autor_lista_textos.html', context, request=request)
            from django.http import HttpResponse
            return HttpResponse(html)

        # Renderiza template normalmente
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Adiciona dados do perfil ao contexto do template.

        Variáveis disponíveis no template:
        - perfil_usuario: objeto User
        - perfil_privado: boolean
        - role_display: texto do role (Autor, Leitor, Administrador)
        - role_badge_class: classe CSS do badge
        - membro_desde: data formatada (ex: "Outubro de 2025")
        - dias_cadastrado: número de dias desde cadastro
        """
        from datetime import datetime
        from django.utils import timezone

        context = super().get_context_data(**kwargs)
        user = self.get_user()

        # Adicionar dados do usuário ao contexto
        context['perfil_usuario'] = user
        # IMPORTANTE: Perfil de AUTOR nunca é privado
        # A privacidade só se aplica ao perfil de LEITOR do autor (/@username/leitor/)
        # Para leitores puros, a privacidade se aplica normalmente
        if user.role in ['AUTOR', 'AUTOR_ADMIN']:
            context['perfil_privado'] = False  # Perfil de autor sempre público
        else:
            context['perfil_privado'] = user.perfil_privado  # Leitores podem ter perfil privado

        # Mapear role para display
        role_map = {
            'AUTOR': 'Autor',
            'LEITOR': 'Leitor',
            'ADMIN': 'Administrador',
            'AUTOR_ADMIN': 'Autor',  # Autor-Admin é exibido como "Autor"
        }
        context['role_display'] = role_map.get(user.role, user.role)

        # Mapear role para classe CSS do badge
        badge_map = {
            'AUTOR': 'bg-primary text-white',  # Laranja
            'AUTOR_ADMIN': 'bg-primary text-white',  # Laranja
            'LEITOR': 'bg-blue-500 text-white',  # Azul
            'ADMIN': 'bg-gray-500 text-white',  # Cinza
        }
        context['role_badge_class'] = badge_map.get(user.role, 'bg-gray-500 text-white')

        # Formatar data de cadastro
        # "Membro desde Outubro de 2025"
        meses = [
            'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ]
        mes = meses[user.date_joined.month - 1]
        ano = user.date_joined.year
        context['membro_desde'] = f"{mes} de {ano}"

        # Calcular dias desde cadastro
        hoje = timezone.now()
        delta = hoje - user.date_joined
        context['dias_cadastrado'] = delta.days

        # Verificar se o usuário logado está seguindo este autor (Item 3.2 do ROADMAP)
        if self.request.user.is_authenticated and user.role == 'AUTOR':
            from apps.usuarios.models import AutorSeguido
            context['seguindo_autor'] = AutorSeguido.objects.filter(
                seguidor=self.request.user,
                autor=user
            ).exists()
        else:
            context['seguindo_autor'] = False

        # Item 1.1 do ROADMAP: Capa/Banner Personalizado
        # Buscar capa escolhida pelo usuário (ou capa padrão se não tiver)
        from apps.usuarios.models import Capa
        capa_escolhida = None
        if hasattr(user, 'configuracao') and user.configuracao.capa_escolhida:
            capa_escolhida = user.configuracao.capa_escolhida
        else:
            # Capa padrão: banner_livros.jpg
            capa_escolhida = Capa.objects.filter(nome='Livros').first()

        context['capa_escolhida'] = capa_escolhida

        # Alinhamento vertical da capa (padrão: centro)
        alinhamento_vertical = 'center'
        if hasattr(user, 'configuracao') and user.configuracao.alinhamento_vertical_capa:
            alinhamento_vertical = user.configuracao.alinhamento_vertical_capa

        context['alinhamento_vertical_capa'] = alinhamento_vertical

        # Verificar se o usuário optou por exibir e-mail no perfil
        exibir_email = False
        if hasattr(user, 'configuracao') and user.configuracao.exibir_email_perfil:
            exibir_email = True
        context['exibir_email_perfil'] = exibir_email

        # Dados do PIX para doações (botão Apoie) - Item 1 do ROADMAP
        # Só para autores com chave PIX cadastrada
        if user.role in ['AUTOR', 'AUTOR_ADMIN']:
            try:
                monetizacao = user.monetizacao_pix
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
                        # Log do erro mas não quebrar a página (botão/widget simplesmente não aparece)
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Erro ao gerar QR Code PIX para autor {user.id}: {str(e)}")
                        context['qrcode_base64'] = None
            except Exception:
                # Monetização PIX não existe para este autor (DoesNotExist)
                pass

        # Imports necessários para todas as seções (autores e não-autores)
        from apps.textos.models import Texto, Visualizacao
        from apps.comentarios.models import Comentario
        from django.db.models import Sum, Count, Q

        # SEÇÃO a) do ROADMAP 1.2: Métricas de Visibilidade do Autor
        # Calcular estatísticas gerais dos textos do autor
        if user.role in ['AUTOR', 'AUTOR_ADMIN']:

            # Buscar todos os textos publicados do autor
            textos_autor = Texto.objects.filter(
                autor=user,
                status=Texto.Status.PUBLICADO,
                is_suspended=False
            )

            # 1. Tempo total de leitura (em segundos)
            # Somar tempo_permanencia de todas as visualizações dos textos do autor
            tempo_total_segundos = Visualizacao.objects.filter(
                texto__in=textos_autor,
                tempo_permanencia__isnull=False
            ).aggregate(total=Sum('tempo_permanencia'))['total'] or 0

            # Converter para horas e minutos para exibição mais legível
            tempo_total_horas = int(tempo_total_segundos // 3600)
            tempo_total_minutos = int((tempo_total_segundos % 3600) // 60)

            # 2. Total de visualizações
            # Contar todas as visualizações dos textos do autor
            total_visualizacoes = Visualizacao.objects.filter(
                texto__in=textos_autor
            ).count()

            # 3. Total de comentários aprovados
            # Contar comentários aprovados nos textos do autor
            total_comentarios = Comentario.objects.filter(
                texto__in=textos_autor,
                status=Comentario.Status.APROVADO
            ).count()

            # Adicionar ao contexto
            context['tempo_total_leitura_horas'] = tempo_total_horas
            context['tempo_total_leitura_minutos'] = tempo_total_minutos
            context['tempo_total_leitura_segundos'] = tempo_total_segundos
            context['total_visualizacoes'] = total_visualizacoes
            context['total_comentarios'] = total_comentarios

            # SEÇÃO b) do ROADMAP 1.2: Acervo dos Meus Textos
            # Lista paginada de textos com filtros e ordenações
            from django.core.paginator import Paginator
            from apps.textos.models import TextoFavorito, TextoLido, TextoLeituraPosterior, CartaoBiblioteca

            # Obter parâmetros de filtro e ordenação da URL
            busca = self.request.GET.get('busca', '')
            ordenacao = self.request.GET.get('ordenacao', 'recentes')
            pagina = self.request.GET.get('pagina', 1)

            # Queryset base: textos publicados do autor
            textos_query = textos_autor

            # Aplicar filtro de busca por título
            if busca:
                textos_query = textos_query.filter(titulo__icontains=busca)

            # Aplicar ordenação
            if ordenacao == 'recentes':
                textos_query = textos_query.order_by('-data_publicacao')
            elif ordenacao == 'antigos':
                textos_query = textos_query.order_by('data_publicacao')
            elif ordenacao == 'mais_vistos':
                # Anotar com count de visualizações e ordenar
                textos_query = textos_query.annotate(
                    num_visualizacoes=Count('visualizacoes')
                ).order_by('-num_visualizacoes')
            elif ordenacao == 'maior_tempo_leitura':
                # Anotar com soma de tempo de leitura e ordenar
                textos_query = textos_query.annotate(
                    tempo_leitura_total=Sum('visualizacoes__tempo_permanencia')
                ).order_by('-tempo_leitura_total')

            # Paginação (10 textos por página)
            paginator = Paginator(textos_query, 10)
            textos_paginados = paginator.get_page(pagina)

            # Adicionar estatísticas para cada texto
            for texto in textos_paginados:
                # Visualizações do texto
                texto.num_visualizacoes = Visualizacao.objects.filter(texto=texto).count()

                # Tempo total de leitura do texto
                tempo_texto = Visualizacao.objects.filter(
                    texto=texto,
                    tempo_permanencia__isnull=False
                ).aggregate(total=Sum('tempo_permanencia'))['total'] or 0
                texto.tempo_leitura_minutos = int(tempo_texto // 60)

                # Comentários do texto
                texto.num_comentarios = Comentario.objects.filter(
                    texto=texto,
                    status=Comentario.Status.APROVADO
                ).count()

            context['textos_paginados'] = textos_paginados
            context['busca'] = busca
            context['ordenacao'] = ordenacao

            # SEÇÃO c) do ROADMAP 1.2: Listas dos 6 Mais
            # Top 6 textos em diferentes categorias

            # 1. Top 6 textos com mais tempo de leitura
            top_tempo_leitura = textos_autor.annotate(
                tempo_total=Sum('visualizacoes__tempo_permanencia')
            ).filter(tempo_total__isnull=False).order_by('-tempo_total')[:6]

            # 2. Top 6 textos mais visualizados
            top_visualizacoes = textos_autor.annotate(
                num_views=Count('visualizacoes')
            ).filter(num_views__gt=0).order_by('-num_views')[:6]

            # 3. Top 6 textos com mais assinaturas nos cartões
            top_cartoes = textos_autor.annotate(
                num_assinaturas=Count('assinaturas')
            ).filter(num_assinaturas__gt=0).order_by('-num_assinaturas')[:6]

            # 4. Top 6 textos mais marcados como melhores (favoritos)
            top_favoritos = textos_autor.annotate(
                num_favoritos=Count('favoritado_por')
            ).filter(num_favoritos__gt=0).order_by('-num_favoritos')[:6]

            # 5. Top 6 textos mais marcados como lidos
            top_lidos = textos_autor.annotate(
                num_lidos=Count('lido_por')
            ).filter(num_lidos__gt=0).order_by('-num_lidos')[:6]

            # 6. Top 6 textos mais salvos em "Ler mais tarde"
            top_ler_depois = textos_autor.annotate(
                num_ler_depois=Count('salvo_para_ler_por')
            ).filter(num_ler_depois__gt=0).order_by('-num_ler_depois')[:6]

            # Adicionar estatísticas detalhadas para cada top 6
            # Top Tempo de Leitura
            for texto in top_tempo_leitura:
                texto.tempo_minutos = int((texto.tempo_total or 0) // 60)
                texto.tempo_horas = int(texto.tempo_minutos // 60)
                texto.tempo_minutos_resto = texto.tempo_minutos % 60

            # Top Visualizações
            for texto in top_visualizacoes:
                texto.total_views = texto.num_views

            # Top Cartões
            for texto in top_cartoes:
                texto.total_assinaturas = texto.num_assinaturas

            # Top Favoritos
            for texto in top_favoritos:
                texto.total_favoritos = texto.num_favoritos

            # Top Lidos
            for texto in top_lidos:
                texto.total_lidos = texto.num_lidos

            # Top Ler Depois
            for texto in top_ler_depois:
                texto.total_ler_depois = texto.num_ler_depois

            # Adicionar ao contexto
            context['top_tempo_leitura'] = top_tempo_leitura
            context['top_visualizacoes'] = top_visualizacoes
            context['top_cartoes'] = top_cartoes
            context['top_favoritos'] = top_favoritos
            context['top_lidos'] = top_lidos
            context['top_ler_depois'] = top_ler_depois

            # SEÇÃO d) do ROADMAP 1.2: Autores Amigos
            # Lista de autores que seguem este autor (seguidores que são autores)
            from apps.usuarios.models import AutorSeguido

            autores_que_seguem = AutorSeguido.objects.filter(
                autor=user
            ).select_related('seguidor').filter(
                seguidor__role__in=['AUTOR', 'AUTOR_ADMIN']
            ).order_by('-data_seguimento')

            # Lista de autores que este autor segue
            autores_que_segue = AutorSeguido.objects.filter(
                seguidor=user
            ).select_related('autor').filter(
                autor__role__in=['AUTOR', 'AUTOR_ADMIN']
            ).order_by('-data_seguimento')

            context['autores_que_seguem'] = autores_que_seguem
            context['autores_que_segue'] = autores_que_segue
            context['total_autores_que_seguem'] = autores_que_seguem.count()
            context['total_autores_que_segue'] = autores_que_segue.count()

            # SEÇÃO e) do ROADMAP 1.2: Meus Seguidores
            # Lista de seguidores que NÃO são autores (leitores e admins)
            # INCLUINDO leitores especiais (que aparecem em ambas as seções)
            # Autores que seguem aparecem na seção "Autores Amigos"
            leitores_seguidores = AutorSeguido.objects.filter(
                autor=user
            ).exclude(
                seguidor__role=User.Role.AUTOR
            ).select_related('seguidor').order_by('-data_seguimento')

            # Lista de usuários que receberam selo de leitor especial
            leitores_especiais = AutorSeguido.objects.filter(
                autor=user,
                is_leitor_especial=True
            ).select_related('seguidor').order_by('-data_seguimento')

            context['leitores_seguidores'] = leitores_seguidores
            context['leitores_especiais'] = leitores_especiais
            context['total_leitores_seguidores'] = leitores_seguidores.count()
            context['total_leitores_especiais'] = leitores_especiais.count()

            # SEÇÃO f) do ROADMAP 1.2: Meus Leitores (Estatísticas Demográficas)
            # Buscar todos os usuários que visualizaram textos deste autor
            from datetime import date
            from django.db.models import Q

            leitores_visualizacoes = User.objects.filter(
                visualizacoes__texto__autor=user,
                visualizacoes__texto__status=Texto.Status.PUBLICADO
            ).distinct()

            # 1. Localizações dos leitores (para o mapa)
            # Agrupar por cidade/país e contar
            from django.db.models import Count
            localizacoes = leitores_visualizacoes.exclude(
                Q(cidade__isnull=True) | Q(cidade='') | Q(pais__isnull=True) | Q(pais='')
            ).values('cidade', 'pais').annotate(
                total=Count('id')
            ).order_by('-total')[:50]  # Top 50 localizações

            context['localizacoes_leitores'] = list(localizacoes)
            context['total_localizacoes'] = len(localizacoes)

            # 2. Distribuição por idade (histograma)
            # Calcular idade de cada leitor e agrupar por faixas etárias
            leitores_com_idade = leitores_visualizacoes.exclude(
                Q(data_nascimento__isnull=True)
            )

            idades = []
            hoje = date.today()
            for leitor in leitores_com_idade:
                idade = hoje.year - leitor.data_nascimento.year
                # Ajustar se ainda não fez aniversário este ano
                if hoje.month < leitor.data_nascimento.month or (
                    hoje.month == leitor.data_nascimento.month and
                    hoje.day < leitor.data_nascimento.day
                ):
                    idade -= 1
                idades.append(idade)

            # Agrupar em faixas etárias
            faixas_etarias = {
                '0-17': 0,
                '18-24': 0,
                '25-34': 0,
                '35-44': 0,
                '45-54': 0,
                '55-64': 0,
                '65+': 0
            }

            for idade in idades:
                if idade < 18:
                    faixas_etarias['0-17'] += 1
                elif idade <= 24:
                    faixas_etarias['18-24'] += 1
                elif idade <= 34:
                    faixas_etarias['25-34'] += 1
                elif idade <= 44:
                    faixas_etarias['35-44'] += 1
                elif idade <= 54:
                    faixas_etarias['45-54'] += 1
                elif idade <= 64:
                    faixas_etarias['55-64'] += 1
                else:
                    faixas_etarias['65+'] += 1

            # Preparar dados para Chart.js (idade)
            context['faixas_etarias_labels'] = list(faixas_etarias.keys())
            context['faixas_etarias_values'] = list(faixas_etarias.values())
            context['total_leitores_com_idade'] = len(idades)

            # 3. Distribuição por sexo (gráfico de pizza)
            distribuicao_sexo = leitores_visualizacoes.exclude(
                sexo=User.Sexo.NAO_DECLARAR
            ).values('sexo').annotate(
                total=Count('id')
            )

            sexo_counts = {'F': 0, 'M': 0, 'O': 0}
            for item in distribuicao_sexo:
                sexo_counts[item['sexo']] = item['total']

            # Preparar dados para Chart.js (sexo)
            sexo_labels_map = {'F': 'Feminino', 'M': 'Masculino', 'O': 'Outro'}
            context['sexo_labels'] = [sexo_labels_map[k] for k in sexo_counts.keys()]
            context['sexo_values'] = list(sexo_counts.values())
            context['total_leitores_sexo_declarado'] = sum(sexo_counts.values())

        # SEÇÃO g) do ROADMAP 1.2: Imersão em leitura
        from apps.textos.models import Visualizacao
        from django.db.models.functions import TruncDate, TruncMonth
        from datetime import timedelta

        # Query de todas as visualizações dos textos publicados do autor
        visualizacoes = Visualizacao.objects.filter(
            texto__autor=user,
            texto__status=Texto.Status.PUBLICADO,
            tempo_permanencia__gt=0  # Apenas visualizações com tempo registrado
        ).order_by('data_visualizacao')

        if visualizacoes.exists():
            # 1. Agregação por DIA
            vis_por_dia = visualizacoes.annotate(
                dia=TruncDate('data_visualizacao')
            ).values('dia').annotate(
                tempo_total=Sum('tempo_permanencia')
            ).order_by('dia')

            # Preparar dados para gráfico diário (últimos 30 dias)
            if vis_por_dia:
                # Pegar últimos 30 registros ou todos se houver menos
                vis_por_dia_recentes = list(vis_por_dia)[-30:]

                context['tempo_diario_labels'] = [
                    item['dia'].strftime('%d/%m/%Y') for item in vis_por_dia_recentes
                ]
                context['tempo_diario_values'] = [
                    round(item['tempo_total'] / 60, 1) for item in vis_por_dia_recentes  # Converter para minutos
                ]
                context['total_dias_com_leitura'] = len(vis_por_dia)
            else:
                context['tempo_diario_labels'] = []
                context['tempo_diario_values'] = []
                context['total_dias_com_leitura'] = 0

            # 2. Agregação por MÊS
            vis_por_mes = visualizacoes.annotate(
                mes=TruncMonth('data_visualizacao')
            ).values('mes').annotate(
                tempo_total=Sum('tempo_permanencia')
            ).order_by('mes')

            # Preparar dados para gráfico mensal (últimos 12 meses)
            if vis_por_mes:
                vis_por_mes_recentes = list(vis_por_mes)[-12:]

                context['tempo_mensal_labels'] = [
                    item['mes'].strftime('%b/%Y') for item in vis_por_mes_recentes
                ]
                context['tempo_mensal_values'] = [
                    round(item['tempo_total'] / 3600, 1) for item in vis_por_mes_recentes  # Converter para horas
                ]
                context['total_meses_com_leitura'] = len(vis_por_mes)
            else:
                context['tempo_mensal_labels'] = []
                context['tempo_mensal_values'] = []
                context['total_meses_com_leitura'] = 0

            # Total geral
            context['total_visualizacoes_com_tempo'] = visualizacoes.count()
        else:
            # Sem dados
            context['tempo_diario_labels'] = []
            context['tempo_diario_values'] = []
            context['total_dias_com_leitura'] = 0
            context['tempo_mensal_labels'] = []
            context['tempo_mensal_values'] = []
            context['total_meses_com_leitura'] = 0
            context['total_visualizacoes_com_tempo'] = 0

        # SEÇÃO b) do ROADMAP 1.1: Suas Listas
        # Item 1.1b: Listas de textos marcados pelo usuário
        # Para não-autores: sempre exibido
        # Para autores: apenas quando visualizando o próprio perfil
        is_proprio_perfil = self.request.user.is_authenticated and self.request.user == user
        deve_exibir_secoes_leitor = user.role not in ['AUTOR', 'AUTOR_ADMIN'] or is_proprio_perfil

        if deve_exibir_secoes_leitor:
            from apps.textos.models import TextoFavorito, TextoLido, TextoLeituraPosterior, CartaoBiblioteca

            # 1. Textos marcados como "melhores" (favoritos) - últimos 6
            textos_favoritos = TextoFavorito.objects.filter(
                usuario=user,
                texto__status=Texto.Status.PUBLICADO,
                texto__is_suspended=False
            ).select_related('texto', 'texto__autor').order_by('-data_favoritado')[:6]
            context['textos_favoritos'] = textos_favoritos
            context['total_favoritos'] = TextoFavorito.objects.filter(
                usuario=user,
                texto__status=Texto.Status.PUBLICADO,
                texto__is_suspended=False
            ).count()

            # 2. Textos marcados como "lidos" - últimos 6
            textos_lidos = TextoLido.objects.filter(
                usuario=user,
                texto__status=Texto.Status.PUBLICADO,
                texto__is_suspended=False
            ).select_related('texto', 'texto__autor').order_by('-data_marcado')[:6]
            context['textos_lidos'] = textos_lidos
            context['total_lidos'] = TextoLido.objects.filter(
                usuario=user,
                texto__status=Texto.Status.PUBLICADO,
                texto__is_suspended=False
            ).count()

            # 3. Textos marcados como "ler mais tarde" - últimos 6
            textos_ler_depois = TextoLeituraPosterior.objects.filter(
                usuario=user,
                texto__status=Texto.Status.PUBLICADO,
                texto__is_suspended=False
            ).select_related('texto', 'texto__autor').order_by('-data_adicionado')[:6]
            context['textos_ler_depois'] = textos_ler_depois
            context['total_ler_depois'] = TextoLeituraPosterior.objects.filter(
                usuario=user,
                texto__status=Texto.Status.PUBLICADO,
                texto__is_suspended=False
            ).count()

            # 4. Textos onde o usuário assinou cartão da biblioteca - últimos 6
            textos_com_assinatura = CartaoBiblioteca.objects.filter(
                usuario=user,
                texto__status=Texto.Status.PUBLICADO,
                texto__is_suspended=False
            ).select_related('texto', 'texto__autor').order_by('-data_assinatura')[:6]
            context['textos_com_assinatura'] = textos_com_assinatura
            context['total_assinaturas'] = CartaoBiblioteca.objects.filter(
                usuario=user,
                texto__status=Texto.Status.PUBLICADO,
                texto__is_suspended=False
            ).count()

            # SEÇÃO c) do ROADMAP 1.1: Notificações
            # Histórico das últimas 6 notificações do usuário
            # IMPORTANTE: Notificações são PESSOAIS - só buscar se for o próprio usuário
            if self.request.user.is_authenticated and self.request.user == user:
                from apps.core.models import Notificacao

                notificacoes_recentes = Notificacao.objects.filter(
                    usuario_destino=user
                ).select_related('motivo', 'usuario_origem').order_by('-data_criacao')[:6]
                context['notificacoes_recentes'] = notificacoes_recentes
                context['total_notificacoes'] = Notificacao.objects.filter(
                    usuario_destino=user
                ).count()
            else:
                context['notificacoes_recentes'] = []
                context['total_notificacoes'] = 0

            # SEÇÃO d) do ROADMAP 1.1: Seus comentários
            # Histórico dos últimos 6 comentários do usuário em textos do site
            # IMPORTANTE: Comentários são PESSOAIS - só buscar se for o próprio usuário
            if self.request.user.is_authenticated and self.request.user == user:
                from apps.comentarios.models import Comentario

                comentarios_recentes = Comentario.objects.filter(
                    autor=user
                ).select_related('texto', 'texto__autor').order_by('-data_publicacao')[:6]
                context['comentarios_recentes'] = comentarios_recentes
                context['total_comentarios_feitos'] = Comentario.objects.filter(
                    autor=user
                ).count()
            else:
                context['comentarios_recentes'] = []
                context['total_comentarios_feitos'] = 0

            # SEÇÃO e) do ROADMAP 1.1: Autores prediletos
            # Duas sublistas: autores seguidos + autores que concederam selo especial
            # IMPORTANTE: Esta seção é PESSOAL mas pode ser visualizada por todos
            # (diferente de notificações/comentários que são privados)
            from apps.usuarios.models import AutorSeguido

            # Sublista 1: Autores que o usuário segue
            autores_seguidos = AutorSeguido.objects.filter(
                seguidor=user
            ).select_related('autor').order_by('-data_seguimento')[:6]
            context['autores_seguidos'] = autores_seguidos
            context['total_autores_seguidos'] = AutorSeguido.objects.filter(
                seguidor=user
            ).count()

            # Sublista 2: Autores que concederam Selo Leitor Especial
            autores_com_selo = AutorSeguido.objects.filter(
                seguidor=user,
                is_leitor_especial=True
            ).select_related('autor').order_by('-data_seguimento')[:6]
            context['autores_com_selo'] = autores_com_selo
            context['total_autores_com_selo'] = AutorSeguido.objects.filter(
                seguidor=user,
                is_leitor_especial=True
            ).count()

            # SEÇÃO f) do ROADMAP 1.1: Imersão em leitura
            from apps.textos.models import Visualizacao
            from django.db.models import Sum, Q
            from django.db.models.functions import TruncDate, TruncMonth
            from datetime import timedelta
            from django.utils import timezone

            # Calcular tempo de leitura por dia (últimos 30 dias)
            data_inicial = timezone.now() - timedelta(days=30)
            tempo_por_dia = Visualizacao.objects.filter(
                usuario=user,
                data_visualizacao__gte=data_inicial,
                tempo_permanencia__isnull=False
            ).annotate(
                dia=TruncDate('data_visualizacao')
            ).values('dia').annotate(
                total_segundos=Sum('tempo_permanencia')
            ).order_by('dia')

            # Converter para formato de gráfico (listas paralelas de labels e dados)
            labels_diarios = []
            dados_diarios = []
            for item in tempo_por_dia:
                labels_diarios.append(item['dia'].strftime('%d/%m'))
                # Converter segundos para minutos
                dados_diarios.append(round(item['total_segundos'] / 60, 2))

            context['labels_diarios'] = labels_diarios
            context['dados_diarios'] = dados_diarios

            # Calcular tempo de leitura por mês (desde o cadastro)
            tempo_por_mes = Visualizacao.objects.filter(
                usuario=user,
                tempo_permanencia__isnull=False
            ).annotate(
                mes=TruncMonth('data_visualizacao')
            ).values('mes').annotate(
                total_segundos=Sum('tempo_permanencia')
            ).order_by('mes')

            # Converter para formato de gráfico
            labels_mensais = []
            dados_mensais = []
            for item in tempo_por_mes:
                labels_mensais.append(item['mes'].strftime('%b/%Y'))
                # Converter segundos para horas
                dados_mensais.append(round(item['total_segundos'] / 3600, 2))

            context['labels_mensais'] = labels_mensais
            context['dados_mensais'] = dados_mensais

            # === Item 5 ROADMAP: Seção "Meus Vizinhos" ===
            # Buscar usuários com gosto similar baseado em:
            # - 40% Autores seguidos em comum
            # - 30% Textos favoritos em comum
            # - 20% Cartões de biblioteca assinados em comum
            # - 10% Textos marcados como lidos em comum
            from apps.usuarios.utils_vizinhos import buscar_vizinhos
            context['vizinhos'] = buscar_vizinhos(user, limite=9)

        # Flag para indicar se deve exibir seções privadas de leitor
        # (para autores, só exibe quando é o próprio perfil)
        context['exibir_secoes_leitor'] = deve_exibir_secoes_leitor if 'deve_exibir_secoes_leitor' in dir() else False

        # Verificar se o usuário do perfil é vizinho do usuário logado (para botão do vilarejo)
        context['perfil_e_vizinho'] = False
        context['vilarejo_do_perfil'] = None
        if self.request.user.is_authenticated and self.request.user != user:
            from apps.usuarios.utils_vizinhos import buscar_vizinhos
            meus_vizinhos = buscar_vizinhos(self.request.user, limite=9)
            for v in meus_vizinhos:
                if v['usuario'].id == user.id:
                    context['perfil_e_vizinho'] = True
                    # Verificar se o usuário do perfil tem vilarejo
                    if hasattr(user, 'vilarejo'):
                        context['vilarejo_do_perfil'] = user.vilarejo
                    break

        return context


class PerfilLeitorAutorView(TemplateView):
    """
    View para exibir o perfil de LEITOR de um autor.

    Acessível via URL: /@username/leitor/ (ex: /@ciniro/leitor/)

    Mostra as estatísticas e dados de leitura do autor, usando o template
    de perfil de leitor (perfil_leitor.html) ao invés do perfil de autor.

    Esta view é acessível APENAS para o próprio autor, pois mostra dados
    privados como favoritos, notificações, comentários, etc.
    """

    template_name = 'usuarios/perfil_leitor.html'

    def get_user(self):
        """
        Busca usuário pelo username da URL.
        Armazena em self.user_profile para reutilização.
        """
        if not hasattr(self, 'user_profile'):
            username = self.kwargs.get('username')
            try:
                self.user_profile = User.objects.get(username=username)
            except User.DoesNotExist:
                self.user_profile = None
        return self.user_profile

    def get(self, request, *args, **kwargs):
        """
        Processa requisição GET.
        - Se usuário não encontrado → redireciona para home
        - Se não é autor → redireciona para perfil normal
        - Se é autor clássico (domínio público) → redireciona para perfil público
        - Se é autor contemporâneo → renderiza perfil de leitor (respeitando privacidade)
        """
        user = self.get_user()

        # Se usuário não existe, redireciona para home
        if not user:
            return redirect('core:home')

        # Se não é autor, redireciona para perfil normal de leitor
        if user.role not in ['AUTOR', 'AUTOR_ADMIN']:
            return redirect('perfil_publico', username=user.username)

        # Se é autor clássico (domínio público), não tem perfil de leitor
        # Redireciona para o perfil público de autor
        if user.is_classico:
            return redirect('perfil_publico', username=user.username)

        # Autor contemporâneo - renderiza perfil de leitor
        # O template cuida de mostrar "perfil privado" se necessário
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Adiciona dados do perfil de LEITOR ao contexto do template.
        Reutiliza a mesma lógica do PerfilPublicoView para não-autores.
        """
        from datetime import datetime, timedelta
        from django.utils import timezone
        from apps.textos.models import Texto, TextoFavorito, TextoLido, TextoLeituraPosterior, CartaoBiblioteca, Visualizacao
        from apps.core.models import Notificacao
        from apps.comentarios.models import Comentario
        from apps.usuarios.models import AutorSeguido, Capa
        from django.db.models import Sum
        from django.db.models.functions import TruncDate, TruncMonth

        context = super().get_context_data(**kwargs)
        user = self.get_user()

        # Adicionar dados básicos do usuário ao contexto
        context['perfil_usuario'] = user
        context['perfil_privado'] = user.perfil_privado  # Respeitar configuração de privacidade
        context['is_perfil_leitor_autor'] = True  # Flag para identificar esta view

        # Mapear role para display (sempre "Leitor" nesta view)
        context['role_display'] = 'Leitor'

        # Mapear role para classe CSS do badge
        context['role_badge_class'] = 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'

        # Data de cadastro formatada
        if user.date_joined:
            meses = {
                1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
                5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
                9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
            }
            context['membro_desde'] = f"{meses[user.date_joined.month]} de {user.date_joined.year}"
            context['dias_cadastrado'] = (timezone.now() - user.date_joined).days
        else:
            context['membro_desde'] = 'Data desconhecida'
            context['dias_cadastrado'] = 0

        # Dados do banner/capa
        capa_escolhida = None
        if hasattr(user, 'configuracao') and user.configuracao.capa_escolhida:
            capa_escolhida = user.configuracao.capa_escolhida
        else:
            capa_escolhida = Capa.objects.filter(nome='Livros').first()
        context['capa_escolhida'] = capa_escolhida

        # Alinhamento vertical da capa
        alinhamento_vertical = 'center'
        if hasattr(user, 'configuracao') and user.configuracao.alinhamento_vertical_capa:
            alinhamento_vertical = user.configuracao.alinhamento_vertical_capa
        context['alinhamento_vertical_capa'] = alinhamento_vertical

        # Verificar se o usuário optou por exibir e-mail no perfil
        exibir_email = False
        if hasattr(user, 'configuracao') and user.configuracao.exibir_email_perfil:
            exibir_email = True
        context['exibir_email_perfil'] = exibir_email

        # SEÇÃO b) - Suas Listas
        # 1. Textos marcados como "melhores" (favoritos)
        textos_favoritos = TextoFavorito.objects.filter(
            usuario=user,
            texto__status=Texto.Status.PUBLICADO,
            texto__is_suspended=False
        ).select_related('texto', 'texto__autor').order_by('-data_favoritado')[:6]
        context['textos_favoritos'] = textos_favoritos
        context['total_favoritos'] = TextoFavorito.objects.filter(
            usuario=user,
            texto__status=Texto.Status.PUBLICADO,
            texto__is_suspended=False
        ).count()

        # 2. Textos marcados como "lidos"
        textos_lidos = TextoLido.objects.filter(
            usuario=user,
            texto__status=Texto.Status.PUBLICADO,
            texto__is_suspended=False
        ).select_related('texto', 'texto__autor').order_by('-data_marcado')[:6]
        context['textos_lidos'] = textos_lidos
        context['total_lidos'] = TextoLido.objects.filter(
            usuario=user,
            texto__status=Texto.Status.PUBLICADO,
            texto__is_suspended=False
        ).count()

        # 3. Textos marcados como "ler mais tarde"
        textos_ler_depois = TextoLeituraPosterior.objects.filter(
            usuario=user,
            texto__status=Texto.Status.PUBLICADO,
            texto__is_suspended=False
        ).select_related('texto', 'texto__autor').order_by('-data_adicionado')[:6]
        context['textos_ler_depois'] = textos_ler_depois
        context['total_ler_depois'] = TextoLeituraPosterior.objects.filter(
            usuario=user,
            texto__status=Texto.Status.PUBLICADO,
            texto__is_suspended=False
        ).count()

        # 4. Textos onde o usuário assinou cartão da biblioteca
        textos_com_assinatura = CartaoBiblioteca.objects.filter(
            usuario=user,
            texto__status=Texto.Status.PUBLICADO,
            texto__is_suspended=False
        ).select_related('texto', 'texto__autor').order_by('-data_assinatura')[:6]
        context['textos_com_assinatura'] = textos_com_assinatura
        context['total_assinaturas'] = CartaoBiblioteca.objects.filter(
            usuario=user,
            texto__status=Texto.Status.PUBLICADO,
            texto__is_suspended=False
        ).count()

        # SEÇÃO c) - Notificações
        notificacoes_recentes = Notificacao.objects.filter(
            usuario_destino=user
        ).select_related('motivo', 'usuario_origem').order_by('-data_criacao')[:6]
        context['notificacoes_recentes'] = notificacoes_recentes
        context['total_notificacoes'] = Notificacao.objects.filter(
            usuario_destino=user
        ).count()

        # SEÇÃO d) - Comentários
        comentarios_recentes = Comentario.objects.filter(
            autor=user
        ).select_related('texto', 'texto__autor').order_by('-data_publicacao')[:6]
        context['comentarios_recentes'] = comentarios_recentes
        context['total_comentarios'] = Comentario.objects.filter(
            autor=user
        ).count()

        # SEÇÃO e) - Autores Prediletos
        # Sublista 1: Autores que o usuário segue
        autores_seguidos = AutorSeguido.objects.filter(
            seguidor=user
        ).select_related('autor').order_by('-data_seguimento')[:6]
        context['autores_seguidos'] = autores_seguidos
        context['total_autores_seguidos'] = AutorSeguido.objects.filter(
            seguidor=user
        ).count()

        # Sublista 2: Autores que concederam Selo Leitor Especial
        autores_com_selo = AutorSeguido.objects.filter(
            seguidor=user,
            is_leitor_especial=True
        ).select_related('autor').order_by('-data_seguimento')[:6]
        context['autores_com_selo'] = autores_com_selo
        context['total_autores_com_selo'] = AutorSeguido.objects.filter(
            seguidor=user,
            is_leitor_especial=True
        ).count()

        # SEÇÃO f) - Imersão em Leitura (Gráficos)
        # Calcular tempo de leitura por dia (últimos 30 dias)
        data_inicial = timezone.now() - timedelta(days=30)
        tempo_por_dia = Visualizacao.objects.filter(
            usuario=user,
            data_visualizacao__gte=data_inicial,
            tempo_permanencia__isnull=False
        ).annotate(
            dia=TruncDate('data_visualizacao')
        ).values('dia').annotate(
            total_segundos=Sum('tempo_permanencia')
        ).order_by('dia')

        # Converter para formato de gráfico
        labels_diarios = []
        dados_diarios = []
        for item in tempo_por_dia:
            labels_diarios.append(item['dia'].strftime('%d/%m'))
            dados_diarios.append(round(item['total_segundos'] / 60, 2))

        context['labels_diarios'] = labels_diarios
        context['dados_diarios'] = dados_diarios

        # Calcular tempo de leitura por mês (desde o cadastro)
        tempo_por_mes = Visualizacao.objects.filter(
            usuario=user,
            tempo_permanencia__isnull=False
        ).annotate(
            mes=TruncMonth('data_visualizacao')
        ).values('mes').annotate(
            total_segundos=Sum('tempo_permanencia')
        ).order_by('mes')

        # Converter para formato de gráfico
        labels_mensais = []
        dados_mensais = []
        for item in tempo_por_mes:
            labels_mensais.append(item['mes'].strftime('%b/%Y'))
            dados_mensais.append(round(item['total_segundos'] / 3600, 2))

        context['labels_mensais'] = labels_mensais
        context['dados_mensais'] = dados_mensais

        # Item 5 ROADMAP: Meus Vizinhos - Leitores com gostos similares
        from apps.usuarios.utils_vizinhos import buscar_vizinhos
        context['vizinhos'] = buscar_vizinhos(user, limite=9)

        # Verificar se o usuário do perfil é vizinho do usuário logado (para botão do vilarejo)
        context['perfil_e_vizinho'] = False
        context['vilarejo_do_perfil'] = None
        if self.request.user.is_authenticated and self.request.user != user:
            meus_vizinhos = buscar_vizinhos(self.request.user, limite=9)
            for v in meus_vizinhos:
                if v['usuario'].id == user.id:
                    context['perfil_e_vizinho'] = True
                    # Verificar se o usuário do perfil tem vilarejo
                    if hasattr(user, 'vilarejo'):
                        context['vilarejo_do_perfil'] = user.vilarejo
                    break

        return context


# ============================================================================
# SEÇÃO b) do ROADMAP 1.1: Páginas "Ver mais" das Listas de Textos
# ============================================================================

class ListaFavoritosView(ListView):
    """
    Mostra TODOS os textos favoritos de um usuário (página completa).

    Rota: /@username/favoritos/
    Template: usuarios/lista_favoritos.html

    IMPORTANTE: Respeita configuração de privacidade do perfil.
    Se perfil_privado=True e usuário não é o dono, retorna 404.
    """
    model = TextoFavorito
    template_name = 'usuarios/lista_favoritos.html'
    context_object_name = 'textos_favoritos'
    paginate_by = 24  # 24 textos por página (grid 4x6)

    def dispatch(self, request, *args, **kwargs):
        """Verifica se o perfil é privado antes de processar a requisição."""
        username = self.kwargs.get('username')
        perfil_usuario = get_object_or_404(User, username=username)

        # Se perfil é privado E usuário não é o dono, redireciona para página de perfil
        # (que já tem tratamento visual apropriado para perfis privados)
        if perfil_usuario.perfil_privado and request.user != perfil_usuario:
            return redirect('perfil_publico', username=username)

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """Retorna todos os textos favoritos do usuário do perfil."""
        username = self.kwargs.get('username')
        user = get_object_or_404(User, username=username)

        return TextoFavorito.objects.filter(
            usuario=user,
            texto__status=Texto.Status.PUBLICADO,
            texto__is_suspended=False
        ).select_related('texto', 'texto__autor').order_by('-data_favoritado')

    def get_context_data(self, **kwargs):
        """Adiciona informações do usuário e dados do banner ao contexto."""
        from datetime import datetime
        from django.utils import timezone
        from apps.usuarios.models import Capa

        context = super().get_context_data(**kwargs)
        username = self.kwargs.get('username')
        user = get_object_or_404(User, username=username)

        context['perfil_usuario'] = user
        context['titulo_lista'] = 'Melhores'
        context['icone'] = 'star'

        # Dados do banner (mesmo do PerfilPublicoView)
        # Role display e badge
        role_map = {
            'AUTOR': 'Autor',
            'LEITOR': 'Leitor',
            'ADMIN': 'Administrador',
            'AUTOR_ADMIN': 'Autor',
        }
        context['role_display'] = role_map.get(user.role, user.role)

        badge_map = {
            'AUTOR': 'bg-primary text-white',
            'AUTOR_ADMIN': 'bg-primary text-white',
            'LEITOR': 'bg-blue-500 text-white',
            'ADMIN': 'bg-gray-500 text-white',
        }
        context['role_badge_class'] = badge_map.get(user.role, 'bg-gray-500 text-white')

        # Membro desde
        meses = [
            'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ]
        mes = meses[user.date_joined.month - 1]
        ano = user.date_joined.year
        context['membro_desde'] = f"{mes} de {ano}"

        # Capa escolhida
        capa_escolhida = None
        if hasattr(user, 'configuracao') and user.configuracao.capa_escolhida:
            capa_escolhida = user.configuracao.capa_escolhida
        else:
            capa_escolhida = Capa.objects.filter(nome='Livros').first()
        context['capa_escolhida'] = capa_escolhida

        # Alinhamento vertical da capa
        alinhamento_vertical = 'center'
        if hasattr(user, 'configuracao') and user.configuracao.alinhamento_vertical_capa:
            alinhamento_vertical = user.configuracao.alinhamento_vertical_capa
        context['alinhamento_vertical_capa'] = alinhamento_vertical

        return context


class ListaLidosView(ListView):
    """
    Mostra TODOS os textos lidos de um usuário (página completa).

    Rota: /@username/lidos/
    Template: usuarios/lista_lidos.html

    IMPORTANTE: Respeita configuração de privacidade do perfil.
    Se perfil_privado=True e usuário não é o dono, retorna 404.
    """
    model = TextoLido
    template_name = 'usuarios/lista_lidos.html'
    context_object_name = 'textos_lidos'
    paginate_by = 24

    def dispatch(self, request, *args, **kwargs):
        """Verifica se o perfil é privado antes de processar a requisição."""
        username = self.kwargs.get('username')
        perfil_usuario = get_object_or_404(User, username=username)

        # Se perfil é privado E usuário não é o dono, redireciona para página de perfil
        # (que já tem tratamento visual apropriado para perfis privados)
        if perfil_usuario.perfil_privado and request.user != perfil_usuario:
            return redirect('perfil_publico', username=username)

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """Retorna todos os textos lidos do usuário do perfil."""
        username = self.kwargs.get('username')
        user = get_object_or_404(User, username=username)

        return TextoLido.objects.filter(
            usuario=user,
            texto__status=Texto.Status.PUBLICADO,
            texto__is_suspended=False
        ).select_related('texto', 'texto__autor').order_by('-data_marcado')

    def get_context_data(self, **kwargs):
        """Adiciona informações do usuário e dados do banner ao contexto."""
        from datetime import datetime
        from django.utils import timezone
        from apps.usuarios.models import Capa

        context = super().get_context_data(**kwargs)
        username = self.kwargs.get('username')
        user = get_object_or_404(User, username=username)

        context['perfil_usuario'] = user
        context['titulo_lista'] = 'Lidos'
        context['icone'] = 'check-circle'

        # Dados do banner
        role_map = {
            'AUTOR': 'Autor',
            'LEITOR': 'Leitor',
            'ADMIN': 'Administrador',
            'AUTOR_ADMIN': 'Autor',
        }
        context['role_display'] = role_map.get(user.role, user.role)

        badge_map = {
            'AUTOR': 'bg-primary text-white',
            'AUTOR_ADMIN': 'bg-primary text-white',
            'LEITOR': 'bg-blue-500 text-white',
            'ADMIN': 'bg-gray-500 text-white',
        }
        context['role_badge_class'] = badge_map.get(user.role, 'bg-gray-500 text-white')

        meses = [
            'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ]
        mes = meses[user.date_joined.month - 1]
        ano = user.date_joined.year
        context['membro_desde'] = f"{mes} de {ano}"

        capa_escolhida = None
        if hasattr(user, 'configuracao') and user.configuracao.capa_escolhida:
            capa_escolhida = user.configuracao.capa_escolhida
        else:
            capa_escolhida = Capa.objects.filter(nome='Livros').first()
        context['capa_escolhida'] = capa_escolhida

        alinhamento_vertical = 'center'
        if hasattr(user, 'configuracao') and user.configuracao.alinhamento_vertical_capa:
            alinhamento_vertical = user.configuracao.alinhamento_vertical_capa
        context['alinhamento_vertical_capa'] = alinhamento_vertical

        return context


class ListaLerDepoisView(ListView):
    """
    Mostra TODOS os textos da lista "Ler Mais Tarde" de um usuário (página completa).

    Rota: /@username/ler-mais-tarde/
    Template: usuarios/lista_ler_depois.html

    IMPORTANTE: Respeita configuração de privacidade do perfil.
    Se perfil_privado=True e usuário não é o dono, retorna 404.
    """
    model = TextoLeituraPosterior
    template_name = 'usuarios/lista_ler_depois.html'
    context_object_name = 'textos_ler_depois'
    paginate_by = 24

    def dispatch(self, request, *args, **kwargs):
        """Verifica se o perfil é privado antes de processar a requisição."""
        username = self.kwargs.get('username')
        perfil_usuario = get_object_or_404(User, username=username)

        # Se perfil é privado E usuário não é o dono, redireciona para página de perfil
        # (que já tem tratamento visual apropriado para perfis privados)
        if perfil_usuario.perfil_privado and request.user != perfil_usuario:
            return redirect('perfil_publico', username=username)

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """Retorna todos os textos da lista 'Ler Mais Tarde' do usuário."""
        username = self.kwargs.get('username')
        user = get_object_or_404(User, username=username)

        return TextoLeituraPosterior.objects.filter(
            usuario=user,
            texto__status=Texto.Status.PUBLICADO,
            texto__is_suspended=False
        ).select_related('texto', 'texto__autor').order_by('-data_adicionado')

    def get_context_data(self, **kwargs):
        """Adiciona informações do usuário e dados do banner ao contexto."""
        from datetime import datetime
        from django.utils import timezone
        from apps.usuarios.models import Capa

        context = super().get_context_data(**kwargs)
        username = self.kwargs.get('username')
        user = get_object_or_404(User, username=username)

        context['perfil_usuario'] = user
        context['titulo_lista'] = 'Ler Mais Tarde'
        context['icone'] = 'bookmark'

        # Dados do banner
        role_map = {
            'AUTOR': 'Autor',
            'LEITOR': 'Leitor',
            'ADMIN': 'Administrador',
            'AUTOR_ADMIN': 'Autor',
        }
        context['role_display'] = role_map.get(user.role, user.role)

        badge_map = {
            'AUTOR': 'bg-primary text-white',
            'AUTOR_ADMIN': 'bg-primary text-white',
            'LEITOR': 'bg-blue-500 text-white',
            'ADMIN': 'bg-gray-500 text-white',
        }
        context['role_badge_class'] = badge_map.get(user.role, 'bg-gray-500 text-white')

        meses = [
            'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ]
        mes = meses[user.date_joined.month - 1]
        ano = user.date_joined.year
        context['membro_desde'] = f"{mes} de {ano}"

        capa_escolhida = None
        if hasattr(user, 'configuracao') and user.configuracao.capa_escolhida:
            capa_escolhida = user.configuracao.capa_escolhida
        else:
            capa_escolhida = Capa.objects.filter(nome='Livros').first()
        context['capa_escolhida'] = capa_escolhida

        alinhamento_vertical = 'center'
        if hasattr(user, 'configuracao') and user.configuracao.alinhamento_vertical_capa:
            alinhamento_vertical = user.configuracao.alinhamento_vertical_capa
        context['alinhamento_vertical_capa'] = alinhamento_vertical

        return context


class ListaCartoesAssinadosView(ListView):
    """
    Mostra TODOS os textos onde o usuário assinou o cartão da biblioteca (página completa).

    Rota: /@username/cartoes-assinados/
    Template: usuarios/lista_cartoes.html

    IMPORTANTE: Respeita configuração de privacidade do perfil.
    Se perfil_privado=True e usuário não é o dono, retorna 404.
    """
    model = CartaoBiblioteca
    template_name = 'usuarios/lista_cartoes.html'
    context_object_name = 'textos_com_assinatura'
    paginate_by = 24

    def dispatch(self, request, *args, **kwargs):
        """Verifica se o perfil é privado antes de processar a requisição."""
        username = self.kwargs.get('username')
        perfil_usuario = get_object_or_404(User, username=username)

        # Se perfil é privado E usuário não é o dono, redireciona para página de perfil
        # (que já tem tratamento visual apropriado para perfis privados)
        if perfil_usuario.perfil_privado and request.user != perfil_usuario:
            return redirect('perfil_publico', username=username)

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """Retorna todos os textos onde o usuário assinou o cartão."""
        username = self.kwargs.get('username')
        user = get_object_or_404(User, username=username)

        return CartaoBiblioteca.objects.filter(
            usuario=user,
            texto__status=Texto.Status.PUBLICADO,
            texto__is_suspended=False
        ).select_related('texto', 'texto__autor').order_by('-data_assinatura')

    def get_context_data(self, **kwargs):
        """Adiciona informações do usuário e dados do banner ao contexto."""
        from datetime import datetime
        from django.utils import timezone
        from apps.usuarios.models import Capa

        context = super().get_context_data(**kwargs)
        username = self.kwargs.get('username')
        user = get_object_or_404(User, username=username)

        context['perfil_usuario'] = user
        context['titulo_lista'] = 'Cartões Assinados'
        context['icone'] = 'document'

        # Dados do banner
        role_map = {
            'AUTOR': 'Autor',
            'LEITOR': 'Leitor',
            'ADMIN': 'Administrador',
            'AUTOR_ADMIN': 'Autor',
        }
        context['role_display'] = role_map.get(user.role, user.role)

        badge_map = {
            'AUTOR': 'bg-primary text-white',
            'AUTOR_ADMIN': 'bg-primary text-white',
            'LEITOR': 'bg-blue-500 text-white',
            'ADMIN': 'bg-gray-500 text-white',
        }
        context['role_badge_class'] = badge_map.get(user.role, 'bg-gray-500 text-white')

        meses = [
            'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ]
        mes = meses[user.date_joined.month - 1]
        ano = user.date_joined.year
        context['membro_desde'] = f"{mes} de {ano}"

        capa_escolhida = None
        if hasattr(user, 'configuracao') and user.configuracao.capa_escolhida:
            capa_escolhida = user.configuracao.capa_escolhida
        else:
            capa_escolhida = Capa.objects.filter(nome='Livros').first()
        context['capa_escolhida'] = capa_escolhida

        alinhamento_vertical = 'center'
        if hasattr(user, 'configuracao') and user.configuracao.alinhamento_vertical_capa:
            alinhamento_vertical = user.configuracao.alinhamento_vertical_capa
        context['alinhamento_vertical_capa'] = alinhamento_vertical

        return context


class ListaNotificacoesView(LoginRequiredMixin, ListView):
    """
    Mostra TODAS as notificações de um usuário (página completa).
    IMPORTANTE: Notificações são PESSOAIS - apenas o próprio usuário pode ver.
    """
    model = Notificacao
    template_name = 'usuarios/lista_notificacoes.html'
    context_object_name = 'notificacoes'
    paginate_by = 24
    login_url = '/contas/entrar/'

    def dispatch(self, request, *args, **kwargs):
        """Verifica se o usuário logado é o dono do perfil."""
        username = self.kwargs.get('username')
        perfil_usuario = get_object_or_404(User, username=username)

        # Apenas o próprio usuário pode ver suas notificações
        if request.user != perfil_usuario:
            return redirect('perfil_publico', username=username)

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """Retorna todas as notificações do usuário."""
        username = self.kwargs.get('username')
        user = get_object_or_404(User, username=username)
        return Notificacao.objects.filter(
            usuario_destino=user
        ).select_related('motivo', 'usuario_origem').order_by('-data_criacao')

    def get_context_data(self, **kwargs):
        """Adiciona dados do perfil e banner ao contexto."""
        context = super().get_context_data(**kwargs)
        username = self.kwargs.get('username')
        user = get_object_or_404(User, username=username)

        # Dados do perfil
        context['perfil_usuario'] = user

        # Mapear role para display
        role_map = {
            'AUTOR': 'Autor',
            'LEITOR': 'Leitor',
            'ADMIN': 'Administrador',
            'AUTOR_ADMIN': 'Autor',
        }
        context['role_display'] = role_map.get(user.role, user.role)

        # Mapear role para classe CSS do badge
        badge_map = {
            'AUTOR': 'bg-primary text-white',
            'AUTOR_ADMIN': 'bg-primary text-white',
            'LEITOR': 'bg-blue-500 text-white',
            'ADMIN': 'bg-gray-500 text-white',
        }
        context['role_badge_class'] = badge_map.get(user.role, 'bg-gray-500 text-white')

        meses = [
            'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ]
        mes = meses[user.date_joined.month - 1]
        ano = user.date_joined.year
        context['membro_desde'] = f"{mes} de {ano}"

        # Capa/Banner
        from apps.usuarios.models import Capa
        capa_escolhida = None
        if hasattr(user, 'configuracao') and user.configuracao.capa_escolhida:
            capa_escolhida = user.configuracao.capa_escolhida
        else:
            capa_escolhida = Capa.objects.filter(nome='Livros').first()
        context['capa_escolhida'] = capa_escolhida

        alinhamento_vertical = 'center'
        if hasattr(user, 'configuracao') and user.configuracao.alinhamento_vertical_capa:
            alinhamento_vertical = user.configuracao.alinhamento_vertical_capa
        context['alinhamento_vertical_capa'] = alinhamento_vertical

        return context


@login_required
def excluir_notificacao(request, notificacao_id):
    """
    Exclui uma notificação do banco de dados.
    IMPORTANTE: Apenas o dono da notificação pode excluí-la.
    """
    from django.http import HttpResponse

    if request.method == 'DELETE' or request.method == 'POST':
        notificacao = get_object_or_404(Notificacao, pk=notificacao_id)

        # Verificar se o usuário é o dono da notificação
        if notificacao.usuario_destino != request.user:
            return HttpResponse(status=403)  # Forbidden

        # Deletar notificação
        notificacao.delete()

        # Retornar resposta vazia (HTMX remove o elemento)
        return HttpResponse(status=200)

    return HttpResponse(status=405)  # Method Not Allowed


# ============================================================================
# SEÇÃO d) do ROADMAP 1.1: Seus comentários - Página completa
# ============================================================================

class ListaComentariosView(LoginRequiredMixin, ListView):
    """
    Mostra TODOS os comentários de um usuário (página completa).
    IMPORTANTE: Comentários são PESSOAIS - apenas o próprio usuário pode ver.

    Rota: /@username/comentarios/
    Template: usuarios/lista_comentarios.html
    """
    model = None  # Definido em get_queryset()
    template_name = 'usuarios/lista_comentarios.html'
    context_object_name = 'comentarios'
    paginate_by = 24
    login_url = '/contas/entrar/'

    def dispatch(self, request, *args, **kwargs):
        """Verifica se o usuário logado é o dono do perfil."""
        username = self.kwargs.get('username')
        perfil_usuario = get_object_or_404(User, username=username)

        # Apenas o próprio usuário pode ver seus comentários
        if request.user != perfil_usuario:
            return redirect('perfil_publico', username=username)

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """Retorna todos os comentários do usuário."""
        from apps.comentarios.models import Comentario

        username = self.kwargs.get('username')
        user = get_object_or_404(User, username=username)

        return Comentario.objects.filter(
            autor=user
        ).select_related('texto', 'texto__autor').order_by('-data_publicacao')

    def get_context_data(self, **kwargs):
        """Adiciona informações do usuário ao contexto."""
        context = super().get_context_data(**kwargs)
        username = self.kwargs.get('username')
        user = get_object_or_404(User, username=username)

        context['perfil_usuario'] = user
        context['total_comentarios'] = self.get_queryset().count()

        # Data de entrada formatada
        meses = [
            'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ]
        mes = meses[user.date_joined.month - 1]
        ano = user.date_joined.year
        context['membro_desde'] = f"{mes} de {ano}"

        # Capa/Banner
        from apps.usuarios.models import Capa
        capa_escolhida = None
        if hasattr(user, 'configuracao') and user.configuracao.capa_escolhida:
            capa_escolhida = user.configuracao.capa_escolhida
        else:
            capa_escolhida = Capa.objects.filter(nome='Livros').first()
        context['capa_escolhida'] = capa_escolhida

        alinhamento_vertical = 'center'
        if hasattr(user, 'configuracao') and user.configuracao.alinhamento_vertical_capa:
            alinhamento_vertical = user.configuracao.alinhamento_vertical_capa
        context['alinhamento_vertical_capa'] = alinhamento_vertical

        return context


@login_required
def excluir_comentario(request, comentario_id):
    """
    Exclui um comentário do banco de dados.
    IMPORTANTE: Apenas o autor do comentário pode excluí-lo.
    """
    from django.http import HttpResponse
    from apps.comentarios.models import Comentario

    if request.method == 'DELETE' or request.method == 'POST':
        comentario = get_object_or_404(Comentario, pk=comentario_id)

        # Verificar se o usuário é o autor do comentário
        if comentario.autor != request.user:
            return HttpResponse(status=403)  # Forbidden

        # Deletar comentário
        comentario.delete()

        # Retornar resposta vazia (HTMX remove o elemento)
        return HttpResponse(status=200)

    return HttpResponse(status=405)  # Method Not Allowed


# ============================================================================
# SEÇÃO e) do ROADMAP 1.1: Autores prediletos - Páginas completas
# ============================================================================

class ListaAutoresSeguidosView(ListView):
    """
    Mostra TODOS os autores que o usuário segue (página completa).

    Rota: /@username/autores-seguidos/
    Template: usuarios/lista_autores_seguidos.html

    IMPORTANTE: Respeita configuração de privacidade do perfil.
    Se perfil_privado=True e usuário não é o dono, redireciona para perfil.
    """
    model = None  # Definido em get_queryset()
    template_name = 'usuarios/lista_autores_seguidos.html'
    context_object_name = 'relacoes'
    paginate_by = 24

    def dispatch(self, request, *args, **kwargs):
        """Verifica se o perfil é privado antes de processar a requisição."""
        username = self.kwargs.get('username')
        perfil_usuario = get_object_or_404(User, username=username)

        # Se perfil é privado E usuário não é o dono, redireciona para página de perfil
        if perfil_usuario.perfil_privado and request.user != perfil_usuario:
            return redirect('perfil_publico', username=username)

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """Retorna todos os autores seguidos pelo usuário."""
        from apps.usuarios.models import AutorSeguido

        username = self.kwargs.get('username')
        user = get_object_or_404(User, username=username)

        return AutorSeguido.objects.filter(
            seguidor=user
        ).select_related('autor').order_by('-data_seguimento')

    def get_context_data(self, **kwargs):
        """Adiciona informações do usuário ao contexto."""
        context = super().get_context_data(**kwargs)
        username = self.kwargs.get('username')
        user = get_object_or_404(User, username=username)

        context['perfil_usuario'] = user
        context['total_autores'] = self.get_queryset().count()

        # Data de entrada formatada
        meses = [
            'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ]
        mes = meses[user.date_joined.month - 1]
        ano = user.date_joined.year
        context['membro_desde'] = f"{mes} de {ano}"

        # Capa/Banner
        from apps.usuarios.models import Capa
        capa_escolhida = None
        if hasattr(user, 'configuracao') and user.configuracao.capa_escolhida:
            capa_escolhida = user.configuracao.capa_escolhida
        else:
            capa_escolhida = Capa.objects.filter(nome='Livros').first()
        context['capa_escolhida'] = capa_escolhida

        alinhamento_vertical = 'center'
        if hasattr(user, 'configuracao') and user.configuracao.alinhamento_vertical_capa:
            alinhamento_vertical = user.configuracao.alinhamento_vertical_capa
        context['alinhamento_vertical_capa'] = alinhamento_vertical

        return context


class ListaSelosEspeciaisView(ListView):
    """
    Mostra TODOS os autores que concederam Selo Leitor Especial ao usuário (página completa).

    Rota: /@username/selos-especiais/
    Template: usuarios/lista_selos_especiais.html

    IMPORTANTE: Respeita configuração de privacidade do perfil.
    Se perfil_privado=True e usuário não é o dono, redireciona para perfil.
    """
    model = None  # Definido em get_queryset()
    template_name = 'usuarios/lista_selos_especiais.html'
    context_object_name = 'relacoes'
    paginate_by = 24

    def dispatch(self, request, *args, **kwargs):
        """Verifica se o perfil é privado antes de processar a requisição."""
        username = self.kwargs.get('username')
        perfil_usuario = get_object_or_404(User, username=username)

        # Se perfil é privado E usuário não é o dono, redireciona para página de perfil
        if perfil_usuario.perfil_privado and request.user != perfil_usuario:
            return redirect('perfil_publico', username=username)

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """Retorna todos os autores que concederam selo especial."""
        from apps.usuarios.models import AutorSeguido

        username = self.kwargs.get('username')
        user = get_object_or_404(User, username=username)

        return AutorSeguido.objects.filter(
            seguidor=user,
            is_leitor_especial=True
        ).select_related('autor').order_by('-data_seguimento')

    def get_context_data(self, **kwargs):
        """Adiciona informações do usuário ao contexto."""
        context = super().get_context_data(**kwargs)
        username = self.kwargs.get('username')
        user = get_object_or_404(User, username=username)

        context['perfil_usuario'] = user
        context['total_autores'] = self.get_queryset().count()

        # Data de entrada formatada
        meses = [
            'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ]
        mes = meses[user.date_joined.month - 1]
        ano = user.date_joined.year
        context['membro_desde'] = f"{mes} de {ano}"

        # Capa/Banner
        from apps.usuarios.models import Capa
        capa_escolhida = None
        if hasattr(user, 'configuracao') and user.configuracao.capa_escolhida:
            capa_escolhida = user.configuracao.capa_escolhida
        else:
            capa_escolhida = Capa.objects.filter(nome='Livros').first()
        context['capa_escolhida'] = capa_escolhida

        alinhamento_vertical = 'center'
        if hasattr(user, 'configuracao') and user.configuracao.alinhamento_vertical_capa:
            alinhamento_vertical = user.configuracao.alinhamento_vertical_capa
        context['alinhamento_vertical_capa'] = alinhamento_vertical

        return context


# ============================================================================
# API: Remover Selo Leitor Especial
# ============================================================================

@login_required
def remover_selo_especial(request, autor_id):
    """
    Remove o Selo Leitor Especial de um autor, mas mantém o seguimento.

    SEÇÃO e) do ROADMAP 1.1: Permite que o usuário remova o selo especial
    de um autor que ele segue, mas continue seguindo o autor normalmente.

    Args:
        request: HttpRequest
        autor_id: ID do autor

    Returns:
        HttpResponse 200 (sucesso) ou 403/404 (erro)
    """
    from django.http import HttpResponse
    from apps.usuarios.models import AutorSeguido

    if request.method == 'POST':
        try:
            # Buscar a relação AutorSeguido
            relacao = get_object_or_404(
                AutorSeguido,
                seguidor=request.user,
                autor_id=autor_id,
                is_leitor_especial=True
            )

            # Apenas remover o selo, mantendo o seguimento
            relacao.is_leitor_especial = False
            relacao.save()

            return HttpResponse(status=200)

        except Exception as e:
            return HttpResponse(status=404)

    return HttpResponse(status=405)  # Method Not Allowed


class ConfiguracoesView(LoginRequiredMixin, UpdateView):
    """
    View para o usuário configurar suas preferências.

    Permite configurar:
    - Conforto de Leitura (Item 4.1.2 do ROADMAP): tema CSS e nível de zoom
    - Notificações (Item 4.1.3 do ROADMAP): e-mails e limite de notificações

    URL: /contas/configuracoes/
    Requer autenticação (LoginRequiredMixin).
    """
    from .models import ConfiguracaoUsuario
    from .forms import ConfiguracoesForm

    model = ConfiguracaoUsuario
    form_class = ConfiguracoesForm
    template_name = 'usuarios/configuracoes.html'
    success_url = reverse_lazy('usuarios:configuracoes')

    def get_object(self, queryset=None):
        """
        Retorna a configuração do usuário logado.

        Se não existir (caso raro), cria automaticamente.
        """
        from .models import ConfiguracaoUsuario

        # Buscar ou criar configuração do usuário logado
        configuracao, created = ConfiguracaoUsuario.objects.get_or_create(
            usuario=self.request.user
        )
        return configuracao

    def get_context_data(self, **kwargs):
        """
        Adiciona temas de leitura e capas de perfil ao contexto.
        """
        context = super().get_context_data(**kwargs)

        # Importar TemaLeitura
        from apps.core.models import TemaLeitura

        # Buscar todos os temas ativos para carregar seus arquivos CSS
        context['temas'] = TemaLeitura.objects.filter(ativo=True)

        # Buscar o tema atual do usuário
        configuracao = self.get_object()
        context['tema_atual_slug'] = configuracao.tema_leitura_padrao.slug if configuracao.tema_leitura_padrao else 'padrao'

        # Item 1.1 do ROADMAP: Capas de Perfil Disponíveis
        from apps.usuarios.models import Capa
        context['capas_disponiveis'] = Capa.objects.filter(ativo=True).order_by('nome')

        # Identificar a capa atualmente em uso (escolhida ou padrão)
        if configuracao.capa_escolhida:
            context['capa_atual_id'] = configuracao.capa_escolhida.id
        else:
            # Capa padrão: Livros
            capa_padrao = Capa.objects.filter(nome='Livros').first()
            context['capa_atual_id'] = capa_padrao.id if capa_padrao else None

        # MELHORIA 73: Calcular se o usuário é maior de 18 anos
        from datetime import date
        hoje = date.today()
        data_nascimento = self.request.user.data_nascimento
        idade = hoje.year - data_nascimento.year - (
            (hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day)
        )
        context['usuario_maior_18'] = idade >= 18

        # Login com Google: verificar se tem conta vinculada
        from allauth.socialaccount.models import SocialAccount
        google_account = SocialAccount.objects.filter(
            user=self.request.user,
            provider='google'
        ).first()
        context['google_vinculado'] = google_account is not None
        context['google_email'] = google_account.extra_data.get('email', '') if google_account else ''

        return context

    def form_valid(self, form):
        """
        Salva as alterações e exibe mensagem de sucesso.

        MELHORIA 73: Força mostrar_aviso_maioridade=True para menores de 18 anos.
        """
        # MELHORIA 73: Verificar idade do usuário
        from datetime import date
        hoje = date.today()
        data_nascimento = self.request.user.data_nascimento
        idade = hoje.year - data_nascimento.year - (
            (hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day)
        )

        # Se usuário é menor de 18 anos, forçar mostrar_aviso_maioridade=True
        if idade < 18:
            form.instance.mostrar_aviso_maioridade = True

        messages.success(
            self.request,
            'Suas configurações foram salvas com sucesso!'
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        """
        Exibe mensagem de erro se houver problemas no formulário.
        """
        messages.error(
            self.request,
            'Houve um erro ao salvar suas configurações. Verifique os campos e tente novamente.'
        )
        return super().form_invalid(form)


@login_required
def alterar_tema_plataforma(request):
    """
    Endpoint AJAX para alterar o tema da plataforma (light/dark) sem reload.

    Recebe o tema via POST e salva no banco de dados imediatamente.
    """
    if request.method != 'POST':
        return HttpResponse(status=405)

    tema = request.POST.get('tema', 'light')

    # Validar valor do tema
    if tema not in ['light', 'dark']:
        return HttpResponse(status=400)

    # Atualizar configuração do usuário
    from apps.usuarios.models import ConfiguracaoUsuario
    configuracao, created = ConfiguracaoUsuario.objects.get_or_create(
        usuario=request.user
    )
    configuracao.tema_plataforma = tema
    configuracao.save()

    return HttpResponse(status=200)


# ============================================================
# ETAPA 7 - Sistema de Selos: Endpoints para Modal de Celebração
# ============================================================

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from apps.usuarios.models import AutorSeguido

@login_required
@require_http_methods(["GET"])
def selo_detalhes_json(request, selo_id):
    """
    Retorna os detalhes de um selo específico em formato JSON.
    
    Usado pelo modal de celebração para exibir informações do autor
    que concedeu o selo.
    """
    try:
        selo = AutorSeguido.objects.select_related('autor').get(
            id=selo_id,
            seguidor=request.user,
            is_leitor_especial=True
        )
        
        return JsonResponse({
            'id': selo.id,
            'autor_nome': selo.autor.get_full_name() or selo.autor.username,  # Nome real, não pseudônimo
            'autor_avatar': selo.autor.get_avatar_url(),
            'autor_username': selo.autor.username,
        })
    except AutorSeguido.DoesNotExist:
        return JsonResponse({'error': 'Selo não encontrado'}, status=404)


@login_required
@require_http_methods(["POST"])
def marcar_selo_exibido(request, selo_id):
    """
    Marca um selo como exibido (selo_especial_modal_exibido = True).

    Chamado quando o usuário fecha o modal de celebração.
    """
    try:
        selo = AutorSeguido.objects.get(
            id=selo_id,
            seguidor=request.user,
            is_leitor_especial=True
        )

        # Marcar como exibido
        selo.selo_especial_modal_exibido = True
        selo.save(update_fields=['selo_especial_modal_exibido'])

        return JsonResponse({'success': True})
    except AutorSeguido.DoesNotExist:
        return JsonResponse({'error': 'Selo não encontrado'}, status=404)


@login_required
@require_http_methods(["POST"])
def limpar_selos_sessao(request):
    """
    Limpa a variável de sessão 'selos_pendentes_ids' após todos os selos
    terem sido exibidos.

    Chamado quando o usuário fecha o último modal de celebração.
    """
    if 'selos_pendentes_ids' in request.session:
        del request.session['selos_pendentes_ids']

    return JsonResponse({'success': True})


@login_required
@require_http_methods(["POST"])
def toggle_visibilidade_perfil(request):
    """
    Alterna a visibilidade do perfil do usuário entre público e privado.

    Seção a) do Item 1.1 do ROADMAP: Permite ao usuário tornar seu perfil
    privado ou público através de um toggle switch.

    Recebe POST com JSON: {"perfil_privado": true/false}
    Retorna JSON: {"success": true} ou {"success": false, "error": "mensagem"}
    """
    import json

    try:
        # Parse do body JSON
        data = json.loads(request.body)
        perfil_privado = data.get('perfil_privado', False)

        # Atualizar campo do usuário
        request.user.perfil_privado = perfil_privado
        request.user.save(update_fields=['perfil_privado'])

        return JsonResponse({'success': True})
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'JSON inválido'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ============================================================
# MELHORIA 73 - Desativar Avisos de Conteúdo Sensível
# ============================================================

@login_required
@require_http_methods(["POST"])
def desativar_avisos_maioridade(request):
    """
    Desativa os avisos de conteúdo sensível para usuários maiores de 18 anos.

    MELHORIA 73: Endpoint chamado quando usuário clica em
    "SIM, exibir o texto e não mostrar essa mensagem novamente"
    na modal de confirmação de idade.

    Requisitos:
    - Usuário deve estar autenticado (login_required)
    - Usuário deve ter 18 anos ou mais
    - Método POST apenas

    Returns:
        JsonResponse com success=True se bem-sucedido
        JsonResponse com erro 403 se menor de 18 anos
        JsonResponse com erro 500 em caso de falha
    """
    try:
        # Verificar idade do usuário
        if request.user.data_nascimento:
            from datetime import date
            hoje = date.today()
            idade = hoje.year - request.user.data_nascimento.year - (
                (hoje.month, hoje.day) < (request.user.data_nascimento.month, request.user.data_nascimento.day)
            )

            # Apenas maiores de 18 podem desativar avisos
            if idade < 18:
                return JsonResponse({
                    'success': False,
                    'error': 'Apenas maiores de 18 anos podem desativar os avisos'
                }, status=403)
        else:
            # Sem data de nascimento = tratar como menor de 18
            return JsonResponse({
                'success': False,
                'error': 'Data de nascimento não cadastrada'
            }, status=403)

        # Desativar avisos na configuração do usuário
        config, created = ConfiguracaoUsuario.objects.get_or_create(usuario=request.user)
        config.mostrar_aviso_maioridade = False
        config.save(update_fields=['mostrar_aviso_maioridade'])

        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ============================================================================
# Views para Login com Google (django-allauth)
# ============================================================================

class ComplementoCadastroGoogleView(FormView):
    """
    View para completar o cadastro de usuários que se registram via Google.

    Quando um novo usuário tenta fazer login com Google e não possui conta,
    o sistema redireciona para esta view para coletar os dados obrigatórios:
    - username (ID de usuário @)
    - data_nascimento
    - aceito_termos

    Após completar o cadastro, o usuário é automaticamente logado e vinculado
    à conta do Google.
    """
    template_name = 'usuarios/complemento_cadastro_google.html'
    form_class = None  # Será importado dinamicamente
    success_url = reverse_lazy('core:home')

    def dispatch(self, request, *args, **kwargs):
        """Verifica se há dados do Google na sessão antes de processar."""
        # Importar form aqui para evitar import circular
        from .forms import ComplementoCadastroGoogleForm
        self.form_class = ComplementoCadastroGoogleForm

        # Verificar se há dados do Google na sessão
        if 'google_signup_data' not in request.session:
            messages.error(
                request,
                'Sessão expirada. Por favor, tente novamente o login com Google.'
            )
            return redirect('usuarios:login')

        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        """Preenche os dados iniciais do formulário com os dados do Google."""
        initial = super().get_initial()

        # Obter dados do Google da sessão
        google_data = self.request.session.get('google_signup_data', {})

        initial['email'] = google_data.get('email', '')
        initial['nome_completo'] = google_data.get('nome_completo', '')

        return initial

    def get_context_data(self, **kwargs):
        """Adiciona dados do Google ao contexto."""
        context = super().get_context_data(**kwargs)

        # Obter dados do Google da sessão
        google_data = self.request.session.get('google_signup_data', {})

        context['google_email'] = google_data.get('email', '')
        context['google_nome'] = google_data.get('nome_completo', '')
        context['google_picture'] = google_data.get('picture', '')

        return context

    def form_valid(self, form):
        """Cria o usuário e vincula à conta do Google."""
        try:
            # Criar o usuário
            user = form.save()

            # Vincular conta do Google
            sociallogin_data = self.request.session.get('socialaccount_sociallogin')
            if sociallogin_data:
                from allauth.socialaccount.models import SocialLogin
                sociallogin = SocialLogin.deserialize(sociallogin_data)
                sociallogin.connect(self.request, user)

            # Limpar dados da sessão
            if 'google_signup_data' in self.request.session:
                del self.request.session['google_signup_data']
            if 'socialaccount_sociallogin' in self.request.session:
                del self.request.session['socialaccount_sociallogin']

            # Fazer login automático
            login(self.request, user, backend='apps.usuarios.backends.EmailBackend')

            # Mensagem de boas-vindas
            messages.success(
                self.request,
                f'Bem-vindo(a) ao LIVRE DIA, {user.first_name}! Seu cadastro foi concluído com sucesso.'
            )

            return super().form_valid(form)

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao completar cadastro via Google: {str(e)}", exc_info=True)

            messages.error(
                self.request,
                'Ocorreu um erro ao completar seu cadastro. Por favor, tente novamente.'
            )
            return self.form_invalid(form)

    def form_invalid(self, form):
        """Adiciona mensagem de erro quando o formulário é inválido."""
        messages.error(
            self.request,
            'Por favor, corrija os erros abaixo para completar seu cadastro.'
        )
        return super().form_invalid(form)


@login_required
def vincular_google(request):
    """
    View para vincular conta Google a um usuário já existente.

    Fluxo:
    1. Usuário clica em "Vincular conta Google" nas configurações
    2. É redirecionado para o OAuth do Google
    3. Após autenticação, o Google redireciona de volta
    4. O adapter do allauth vincula automaticamente se o email coincidir
    """
    from allauth.socialaccount.models import SocialAccount

    # Verificar se já tem conta Google vinculada
    if SocialAccount.objects.filter(user=request.user, provider='google').exists():
        messages.info(request, 'Sua conta Google já está vinculada.')
        return redirect('usuarios:configuracoes')

    # Redirecionar para o fluxo OAuth do Google
    # O allauth cuidará do resto
    return redirect('google_login')


@login_required
def desvincular_google(request):
    """
    View para desvincular conta Google de um usuário.

    IMPORTANTE: Só permite desvincular se o usuário tiver uma senha definida,
    caso contrário ficaria sem forma de login.
    """
    from allauth.socialaccount.models import SocialAccount

    if request.method != 'POST':
        return redirect('usuarios:configuracoes')

    # Verificar se o usuário tem senha definida
    if not request.user.has_usable_password():
        messages.error(
            request,
            'Você não pode desvincular sua conta Google pois não possui senha cadastrada. '
            'Defina uma senha primeiro em "Minha Conta".'
        )
        return redirect('usuarios:configuracoes')

    # Remover vinculação
    try:
        social_account = SocialAccount.objects.get(user=request.user, provider='google')
        social_account.delete()
        messages.success(request, 'Sua conta Google foi desvinculada com sucesso.')
    except SocialAccount.DoesNotExist:
        messages.info(request, 'Você não possui conta Google vinculada.')

    return redirect('usuarios:configuracoes')


def google_has_account(user):
    """
    Função auxiliar para verificar se o usuário tem conta Google vinculada.
    Pode ser usada em templates via template tag.
    """
    from allauth.socialaccount.models import SocialAccount
    return SocialAccount.objects.filter(user=user, provider='google').exists()


def get_google_account_email(user):
    """
    Retorna o email da conta Google vinculada ao usuário.
    Retorna None se não houver conta vinculada.
    """
    from allauth.socialaccount.models import SocialAccount
    try:
        social_account = SocialAccount.objects.get(user=user, provider='google')
        return social_account.extra_data.get('email', '')
    except SocialAccount.DoesNotExist:
        return None


@login_required
def backup_textos_autor(request):
    """
    Gera um arquivo .docx com todos os textos publicados do autor.

    O arquivo contém para cada texto:
    - Título
    - Subtítulo (se houver)
    - Data de Publicação
    - Categorias (tags)
    - Conteúdo do texto

    Apenas usuários com role=AUTOR podem acessar esta view.
    """
    from docx import Document
    from docx.shared import Pt, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from html import unescape
    import re
    from io import BytesIO
    from datetime import datetime

    user = request.user

    # Verificar se é autor
    if user.role != 'AUTOR':
        messages.error(request, 'Apenas autores podem fazer backup de textos.')
        return redirect('usuarios:minha_conta')

    # Buscar textos publicados do autor
    textos = Texto.objects.filter(
        autor=user,
        status='PUBLICADO'
    ).prefetch_related('tags').order_by('-data_publicacao')

    if not textos.exists():
        messages.info(request, 'Você ainda não possui textos publicados para backup.')
        return redirect('usuarios:minha_conta')

    # Criar documento Word
    doc = Document()

    # Configurar título do documento
    nome_autor = user.get_full_name() or user.username
    titulo_doc = doc.add_heading(f'Backup de Textos - {nome_autor}', 0)
    titulo_doc.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Adicionar data do backup
    data_backup = doc.add_paragraph()
    data_backup.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = data_backup.add_run(f'Gerado em: {datetime.now().strftime("%d/%m/%Y às %H:%M")}')
    run.italic = True

    # Adicionar informação de quantidade
    info = doc.add_paragraph()
    info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = info.add_run(f'Total de textos: {textos.count()}')
    run.bold = True

    doc.add_paragraph()  # Espaço

    # Função para limpar HTML e extrair texto puro
    def html_para_texto(html_content):
        if not html_content:
            return ''
        # Substituir <br> por quebras de linha
        texto = re.sub(r'<br\s*/?>', '\n', html_content)
        # Substituir </p> por quebras de linha duplas
        texto = re.sub(r'</p>', '\n\n', texto)
        # Remover todas as outras tags HTML
        texto = re.sub(r'<[^>]+>', '', texto)
        # Decodificar entidades HTML
        texto = unescape(texto)
        # Limpar espaços extras
        texto = re.sub(r'\n{3,}', '\n\n', texto)
        return texto.strip()

    # Adicionar cada texto
    for i, texto in enumerate(textos, 1):
        # Título do texto
        heading = doc.add_heading(f'{i}. {texto.titulo}', level=1)

        # Subtítulo (se houver)
        if texto.subtitulo:
            subtitulo_p = doc.add_paragraph()
            run = subtitulo_p.add_run(texto.subtitulo)
            run.italic = True
            run.font.size = Pt(12)

        # Metadados
        meta = doc.add_paragraph()

        # Data de publicação
        if texto.data_publicacao:
            data_pub = texto.data_publicacao.strftime('%d/%m/%Y')
            run = meta.add_run(f'Publicado em: {data_pub}')
            run.bold = True

        # Tags/Categorias
        tags = texto.tags.all()
        if tags:
            tags_str = ', '.join([tag.nome for tag in tags])
            meta.add_run('\n')
            run = meta.add_run(f'Categorias: {tags_str}')

        doc.add_paragraph()  # Espaço

        # Conteúdo do texto
        conteudo = html_para_texto(texto.conteudo)
        if conteudo:
            # Dividir em parágrafos
            paragrafos = conteudo.split('\n\n')
            for paragrafo in paragrafos:
                if paragrafo.strip():
                    p = doc.add_paragraph(paragrafo.strip())
                    p.paragraph_format.first_line_indent = Inches(0.5)

        # Linha separadora entre textos
        if i < textos.count():
            doc.add_paragraph('─' * 50)
            doc.add_paragraph()

    # Salvar em buffer
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    # Preparar resposta HTTP
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

    # Nome do arquivo com data
    nome_arquivo = f'backup_textos_{user.username}_{datetime.now().strftime("%Y%m%d")}.docx'
    response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'

    return response


# =============================================================================
# GERENCIAMENTO DE PREFERÊNCIAS DE E-MAIL VIA TOKEN
# =============================================================================

def gerar_token_email_prefs(user_id):
    """
    Gera um token seguro para o link de preferências de e-mail.
    O token expira em 30 dias.
    """
    from django.core import signing

    return signing.dumps({'user_id': user_id}, salt='email-preferences')


def verificar_token_email_prefs(token):
    """
    Verifica e decodifica o token de preferências de e-mail.
    Retorna o user_id se válido, None se inválido ou expirado.
    """
    from django.core import signing

    try:
        # Token válido por 30 dias
        data = signing.loads(token, salt='email-preferences', max_age=60 * 60 * 24 * 30)
        return data.get('user_id')
    except (signing.BadSignature, signing.SignatureExpired):
        return None


def email_preferences_view(request, token):
    """
    View para gerenciar preferências de e-mail via link do e-mail.

    Verifica se:
    1. O token é válido
    2. O usuário logado (se houver) é o mesmo do token

    Se o usuário estiver logado como outra pessoa, mostra mensagem de erro.
    Se não estiver logado, redireciona para login.
    """
    from django.contrib.auth import get_user_model
    from django.contrib import messages
    from .models import ConfiguracaoUsuario

    User = get_user_model()

    # Verificar token
    user_id = verificar_token_email_prefs(token)

    if user_id is None:
        # Token inválido ou expirado
        messages.error(
            request,
            'Este link expirou ou é inválido. Por favor, faça login e acesse suas configurações diretamente.'
        )
        return redirect('usuarios:login')

    # Buscar usuário do token
    try:
        token_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'Usuário não encontrado.')
        return redirect('usuarios:login')

    # Verificar se há usuário logado
    if request.user.is_authenticated:
        # Verificar se é o mesmo usuário
        if request.user.id != user_id:
            # Usuário logado é diferente do usuário do token
            messages.warning(
                request,
                f'Você está logado como {request.user.get_full_name() or request.user.username}. '
                f'Este link é para a conta de {token_user.email}. '
                f'Por favor, faça logout e acesse novamente com a conta correta.'
            )
            return render(request, 'usuarios/email_prefs_erro.html', {
                'usuario_logado': request.user,
                'usuario_token': token_user,
            })

        # Usuário correto - redirecionar para configurações com parâmetro
        return redirect('usuarios:configuracoes')
    else:
        # Usuário não está logado - redirecionar para login e depois para configurações
        messages.info(
            request,
            f'Por favor, faça login com a conta {token_user.email} para gerenciar suas preferências de e-mail.'
        )
        # Salvar na sessão para redirecionar após login
        request.session['email_prefs_redirect'] = True
        return redirect(f"{reverse('usuarios:login')}?next={reverse('usuarios:configuracoes')}")
