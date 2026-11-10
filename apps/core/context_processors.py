"""
Context processors customizados do app core.

Context processors fornecem variáveis globais para todos os templates.
"""


def tema_plataforma(request):
    """
    Context processor para o tema da plataforma (light/dark).

    Disponibiliza para todos os templates:
    - tema_plataforma: 'light' ou 'dark' (padrão: 'light')

    A classe do tema é usada no elemento <html> do base.html para
    aplicar os estilos corretos do Tailwind CSS.

    Args:
        request: HttpRequest

    Returns:
        dict: Dicionário com a variável tema_plataforma
    """
    # Valor padrão: light (para usuários não autenticados)
    tema = 'light'

    # Se usuário estiver autenticado, buscar configuração
    if request.user.is_authenticated:
        try:
            configuracao = request.user.configuracao
            tema = configuracao.tema_plataforma or 'light'
        except Exception:
            # Se houver erro, usar tema padrão
            pass

    return {'tema_plataforma': tema}


def notificacoes(request):
    """
    Context processor para informações de notificações.

    Disponibiliza para todos os templates:
    - exibir_sino: se o usuário configurou para exibir o sino
    - total_notificacoes_nao_lidas: quantidade de notificações não lidas

    Args:
        request: HttpRequest

    Returns:
        dict: Dicionário com variáveis de contexto
    """
    # Valores padrão para usuários não autenticados
    context = {
        'exibir_sino': False,
        'total_notificacoes_nao_lidas': 0,
    }

    # Se usuário estiver autenticado, buscar configurações
    if request.user.is_authenticated:
        try:
            configuracao = request.user.configuracao
            exibir_sino = configuracao.exibir_sininho_notificacoes

            # Se usuário quer exibir sino, contar notificações não lidas
            if exibir_sino:
                from apps.core.models import Notificacao
                total_nao_lidas = Notificacao.objects.filter(
                    usuario_destino=request.user,
                    lida=False
                ).count()

                context = {
                    'exibir_sino': True,
                    'total_notificacoes_nao_lidas': total_nao_lidas,
                }
        except Exception:
            # Se houver erro (ex: configuração não existe), retornar valores padrão
            pass

    return context


def convites_autor(request):
    """
    Context processor para informações de convites do autor.

    Disponibiliza para todos os templates:
    - convites_autor_restantes: quantidade de convites restantes
    - convites_autor_limite: limite total de convites
    - convites_autor_sem_convites: True se não há mais convites

    Valores são 0/False para não autores.

    Args:
        request: HttpRequest

    Returns:
        dict: Dicionário com variáveis de contexto de convites
    """
    # Valores padrão para usuários não autenticados ou não autores
    context = {
        'convites_autor_restantes': 0,
        'convites_autor_limite': 0,
        'convites_autor_sem_convites': True,
    }

    # Se usuário estiver autenticado e for autor
    if request.user.is_authenticated and request.user.role == 'AUTOR':
        try:
            from apps.painel_admin.models import ConviteAutor, ConfiguracaoSistema

            # Obter configuração do sistema
            config = ConfiguracaoSistema.get_config()
            limite = config.limite_convites_autor

            # Contar convites utilizados (apenas ativados contam)
            utilizados = ConviteAutor.objects.filter(
                convidado_por=request.user,
                ativado=True
            ).count()

            restantes = max(0, limite - utilizados)

            context = {
                'convites_autor_restantes': restantes,
                'convites_autor_limite': limite,
                'convites_autor_sem_convites': restantes == 0,
            }
        except Exception:
            # Se houver erro, retornar valores padrão
            pass

    return context
