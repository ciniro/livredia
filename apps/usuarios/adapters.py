"""
Adapters customizados para django-allauth.

Este módulo contém os adapters que personalizam o comportamento do django-allauth
para integrar com o sistema de autenticação do Livre Dia.

Fluxos implementados:
1. Login com Google para usuário existente → Vincula automaticamente e faz login
2. Login com Google para novo usuário → Redireciona para formulário de complemento
3. Vinculação de conta Google na área de configurações

Autor: Claude Code
Data: Dezembro 2025
"""

from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import HttpResponseRedirect

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse

User = get_user_model()


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Adapter customizado para o sistema de contas do allauth.

    Personaliza o comportamento padrão do allauth para:
    - Desabilitar cadastro direto via allauth (usamos nosso próprio formulário)
    - Redirecionar para nossas URLs customizadas
    """

    def is_open_for_signup(self, request):
        """
        Desabilita o cadastro via formulários padrão do allauth.
        O cadastro de leitores é feito via nosso formulário customizado.
        """
        return False

    def get_login_redirect_url(self, request):
        """
        Redireciona após login bem-sucedido baseado no perfil do usuário.

        Ordem de prioridade:
        1. Parâmetro 'next' da sessão (se existir)
        2. Redirecionamento baseado no perfil do usuário:
           - ADMIN → /painel-admin/
           - AUTOR → /autor/
           - LEITOR → /
        """
        # Verificar se existe parâmetro 'next' na sessão
        next_url = request.session.get('next')
        if next_url:
            del request.session['next']
            return next_url

        user = request.user

        if user.is_authenticated:
            # Administradores puros (ADMIN) → Área Administrativa
            if user.role == 'ADMIN':
                return reverse('painel_admin:dashboard')

            # Autores (AUTOR, com ou sem is_admin) → Área do Autor
            elif user.role == 'AUTOR':
                return reverse('painel_autor:dashboard')

        # Fallback: Home
        return reverse('core:home')


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Adapter customizado para contas sociais (Google).

    Personaliza o comportamento do allauth para:
    - Vincular automaticamente se o email já existe no sistema
    - Redirecionar para formulário de complemento se for novo usuário
    - Marcar email como verificado automaticamente (vem do Google)
    """

    def pre_social_login(self, request, sociallogin):
        """
        Executado ANTES do login social ser processado.

        Verifica se o email do Google já existe no sistema:
        - Se existe: Vincula a conta social ao usuário existente
        - Se não existe: Salva dados na sessão e redireciona para complemento
        """
        # Se o usuário já está autenticado, estamos vinculando uma conta
        if request.user.is_authenticated:
            return

        # Se já existe um usuário vinculado a esta conta social, prosseguir com login
        if sociallogin.is_existing:
            return

        # Obter email da conta social
        email = sociallogin.account.extra_data.get('email')
        if not email:
            # Se não tiver email, mostrar erro
            messages.error(
                request,
                'Não foi possível obter seu email da conta Google. '
                'Por favor, tente novamente ou use o cadastro tradicional.'
            )
            raise ImmediateHttpResponse(
                HttpResponseRedirect(reverse('usuarios:login'))
            )

        # Verificar se já existe um usuário com este email
        try:
            existing_user = User.objects.get(email=email)

            # Verificar se o usuário está suspenso
            if existing_user.is_suspended:
                messages.error(
                    request,
                    'Você foi suspenso pelo LIVRE DIA. Se desejar, entre em contato através do formulário em Fale Conosco.'
                )
                raise ImmediateHttpResponse(
                    HttpResponseRedirect(reverse('usuarios:login'))
                )

            # Vincular a conta social ao usuário existente
            sociallogin.connect(request, existing_user)

            # Marcar email como verificado (veio do Google)
            if not existing_user.email_verified:
                existing_user.email_verified = True
                existing_user.save(update_fields=['email_verified'])

            # O login prosseguirá normalmente

        except User.DoesNotExist:
            # Usuário não existe - salvar dados na sessão e redirecionar
            extra_data = sociallogin.account.extra_data

            # Salvar dados do Google na sessão para uso posterior
            request.session['google_signup_data'] = {
                'email': extra_data.get('email', ''),
                'nome_completo': extra_data.get('name', ''),
                'first_name': extra_data.get('given_name', ''),
                'last_name': extra_data.get('family_name', ''),
                'picture': extra_data.get('picture', ''),
                'google_id': extra_data.get('sub', ''),
            }

            # Armazenar o sociallogin serializado para vincular depois
            request.session['socialaccount_sociallogin'] = sociallogin.serialize()
            request.session.modified = True

            # Redirecionar para nosso formulário de complemento
            raise ImmediateHttpResponse(
                HttpResponseRedirect(reverse('usuarios:complemento_cadastro_google'))
            )

    def is_open_for_signup(self, request, sociallogin):
        """
        Permite "signup" via conta social.

        Este método é chamado quando o allauth verifica se pode criar um novo usuário.
        Retornamos True, mas na prática o pre_social_login já redirecionou para
        nosso formulário de complemento.
        """
        return True

    def on_authentication_error(
        self,
        request,
        provider_id,
        error=None,
        exception=None,
        extra_context=None,
    ):
        """
        Trata erros de autenticação social (método atualizado do allauth).
        """
        messages.error(
            request,
            'Ocorreu um erro ao tentar fazer login com o Google. '
            'Por favor, tente novamente ou use o login tradicional.'
        )
        return HttpResponseRedirect(reverse('usuarios:login'))
