"""
Template tags e filtros para processamento de e-mails.

Funções para detectar provedor de e-mail e gerar botões
de redirecionamento para webmail.
"""

from django import template

register = template.Library()

# Mapeamento: domínio → (nome_provedor, url_webmail, tem_icone_custom)
EMAIL_PROVIDERS = {
    'gmail.com': ('Gmail', 'https://mail.google.com', True),
    'googlemail.com': ('Gmail', 'https://mail.google.com', True),
    'outlook.com': ('Outlook', 'https://outlook.live.com', True),
    'hotmail.com': ('Hotmail', 'https://outlook.live.com', True),
    'live.com': ('Outlook', 'https://outlook.live.com', True),
    'yahoo.com': ('Yahoo Mail', 'https://mail.yahoo.com', True),
    'yahoo.com.br': ('Yahoo Mail', 'https://mail.yahoo.com', True),
    'uol.com.br': ('UOL', 'https://email.uol.com.br', True),
    'bol.com.br': ('BOL', 'https://email.bol.com.br', False),
    'icloud.com': ('iCloud', 'https://www.icloud.com/mail', True),
    'me.com': ('iCloud', 'https://www.icloud.com/mail', True),
    'protonmail.com': ('ProtonMail', 'https://mail.protonmail.com', True),
    'proton.me': ('ProtonMail', 'https://mail.proton.me', True),
}


@register.filter
def get_email_domain(email):
    """
    Extrai o domínio de um endereço de e-mail.

    Args:
        email (str): Endereço de e-mail completo

    Returns:
        str: Domínio do e-mail em minúsculas, ou string vazia se inválido

    Exemplo:
        'usuario@gmail.com' → 'gmail.com'
    """
    if not email or '@' not in str(email):
        return ''

    try:
        return str(email).split('@')[1].lower().strip()
    except (IndexError, AttributeError):
        return ''


@register.filter
def get_email_provider_info(email):
    """
    Retorna informações do provedor de e-mail baseado no domínio.

    Args:
        email (str): Endereço de e-mail completo

    Returns:
        dict: Dicionário com informações do provedor:
            - name (str): Nome legível do provedor
            - url (str): URL do webmail
            - has_custom_icon (bool): Se tem ícone customizado
            - domain (str): Domínio extraído

    Exemplo:
        'usuario@gmail.com' → {
            'name': 'Gmail',
            'url': 'https://mail.google.com',
            'has_custom_icon': True,
            'domain': 'gmail.com'
        }
    """
    domain = get_email_domain(email)

    if domain in EMAIL_PROVIDERS:
        name, url, has_custom_icon = EMAIL_PROVIDERS[domain]
        return {
            'name': name,
            'url': url,
            'has_custom_icon': has_custom_icon,
            'domain': domain
        }

    # Provedor não cadastrado - usar informações genéricas
    return {
        'name': 'seu E-mail',
        'url': f'https://{domain}' if domain else '#',
        'has_custom_icon': False,
        'domain': domain
    }
