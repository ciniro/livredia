from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailBackend(ModelBackend):
    """
    Backend de autenticacao customizado que permite login com email.

    O usuario pode fazer login usando:
    - E-mail + Senha (conforme prototipo)
    - Username + Senha (padrao Django)

    Regras adicionais:
    - Autores classicos (is_classico=True) sao bloqueados se a configuracao
      'autores_classicos_podem_login' estiver desabilitada
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Tenta autenticar o usuario com email ou username.

        Args:
            request: HttpRequest object
            username: pode ser email ou username
            password: senha do usuario

        Returns:
            User object se autenticado, None caso contrario
        """
        if username is None or password is None:
            return None

        try:
            # Primeiro tenta encontrar por email
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            try:
                # Se nao encontrar, tenta por username
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                # Executa hasher padrao para evitar timing attacks
                User().set_password(password)
                return None

        # Verifica a senha
        if user.check_password(password) and self.user_can_authenticate(user):
            # Verificar se e autor classico e se pode fazer login
            if user.is_classico:
                from apps.painel_admin.models import ConfiguracaoSistema
                config = ConfiguracaoSistema.get_config()
                if not config.autores_classicos_podem_login:
                    # Autor classico bloqueado
                    return None

            return user

        return None
