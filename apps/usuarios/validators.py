"""
Validadores customizados para chaves PIX.

Implementa validação rigorosa de formato para os 5 tipos de chave PIX
aceitos pelo Banco Central do Brasil, seguindo especificações oficiais.

Tipos de chave suportados:
- CPF: 11 dígitos numéricos
- CNPJ: 14 dígitos numéricos
- E-mail: Formato padrão RFC 5322
- Telefone: Formato internacional (+55 + DDD + número)
- Chave Aleatória (EVP): UUID de 32 caracteres hexadecimais
"""

import re
from django.core.exceptions import ValidationError


def validar_cpf_pix(valor):
    """
    Valida formato de chave PIX tipo CPF.

    Args:
        valor (str): CPF informado (com ou sem formatação)

    Returns:
        str: CPF limpo (somente dígitos)

    Raises:
        ValidationError: Se formato for inválido
    """
    if not valor:
        raise ValidationError('CPF não pode ser vazio.')

    # Remove pontuação e espaços
    cpf_limpo = re.sub(r'[^\d]', '', valor)

    # Valida: exatamente 11 dígitos numéricos
    if not re.match(r'^\d{11}$', cpf_limpo):
        raise ValidationError(
            'CPF deve conter exatamente 11 dígitos numéricos. '
            'Exemplo: 12345678901 ou 123.456.789-01'
        )

    # Verifica CPFs com todos os dígitos iguais (inválidos)
    if cpf_limpo == cpf_limpo[0] * 11:
        raise ValidationError('CPF inválido: todos os dígitos são iguais.')

    return cpf_limpo


def validar_cnpj_pix(valor):
    """
    Valida formato de chave PIX tipo CNPJ.

    Args:
        valor (str): CNPJ informado (com ou sem formatação)

    Returns:
        str: CNPJ limpo (somente dígitos)

    Raises:
        ValidationError: Se formato for inválido
    """
    if not valor:
        raise ValidationError('CNPJ não pode ser vazio.')

    # Remove pontuação e espaços
    cnpj_limpo = re.sub(r'[^\d]', '', valor)

    # Valida: exatamente 14 dígitos numéricos
    if not re.match(r'^\d{14}$', cnpj_limpo):
        raise ValidationError(
            'CNPJ deve conter exatamente 14 dígitos numéricos. '
            'Exemplo: 12345678000190 ou 12.345.678/0001-90'
        )

    # Verifica CNPJs com todos os dígitos iguais (inválidos)
    if cnpj_limpo == cnpj_limpo[0] * 14:
        raise ValidationError('CNPJ inválido: todos os dígitos são iguais.')

    return cnpj_limpo


def validar_email_pix(valor):
    """
    Valida formato de chave PIX tipo E-mail.

    Args:
        valor (str): E-mail informado

    Returns:
        str: E-mail normalizado (lowercase, sem espaços)

    Raises:
        ValidationError: Se formato for inválido
    """
    if not valor:
        raise ValidationError('E-mail não pode ser vazio.')

    # Normaliza: remove espaços e converte para minúsculas
    email_normalizado = valor.strip().lower()

    # Regex simplificado mas robusto para e-mail (RFC 5322 básico)
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not re.match(email_regex, email_normalizado):
        raise ValidationError(
            'Formato de e-mail inválido. '
            'Exemplo: seuemail@dominio.com.br'
        )

    # Validação adicional: tamanho máximo (padrão RFC 5321)
    if len(email_normalizado) > 254:
        raise ValidationError('E-mail muito longo (máximo 254 caracteres).')

    return email_normalizado


def validar_telefone_pix(valor):
    """
    Valida formato de chave PIX tipo Telefone.

    Formato aceito: +55 + DDD (2 dígitos) + Número (8 ou 9 dígitos)
    Exemplos válidos:
    - +5561912345678 (celular com 9 dígitos)
    - +556134567890 (fixo com 8 dígitos)

    Args:
        valor (str): Telefone informado

    Returns:
        str: Telefone formatado no padrão internacional

    Raises:
        ValidationError: Se formato for inválido
    """
    if not valor:
        raise ValidationError('Telefone não pode ser vazio.')

    # Remove espaços, parênteses e hífens (mantém + e dígitos)
    telefone_limpo = re.sub(r'[^\d+]', '', valor)

    # Valida: +55 + DDD (2 dígitos) + Número (8 ou 9 dígitos)
    # Total: 13 ou 14 caracteres
    if not re.match(r'^\+55\d{10,11}$', telefone_limpo):
        raise ValidationError(
            'Telefone deve estar no formato internacional: +55 + DDD + Número. '
            'Exemplos: +5561912345678 (celular) ou +556134567890 (fixo)'
        )

    # Extrai DDD para validação adicional
    ddd = telefone_limpo[3:5]

    # Lista de DDDs válidos no Brasil (11 a 99, exceto alguns não utilizados)
    ddds_invalidos = ['00', '01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '20', '23', '25', '26', '29', '30', '36', '39', '40', '50', '52', '56', '57', '58', '59', '60', '70', '72', '76', '78', '80', '90']

    if ddd in ddds_invalidos:
        raise ValidationError(f'DDD {ddd} não é válido no Brasil.')

    return telefone_limpo


def validar_chave_aleatoria_pix(valor):
    """
    Valida formato de chave PIX tipo Aleatória (EVP - Endereço Virtual de Pagamento).

    Formato: UUID de 32 caracteres hexadecimais (com ou sem hífens)
    Exemplos válidos:
    - 123e4567-e89b-12d3-a456-426614174000 (com hífens)
    - 123e4567e89b12d3a456426614174000 (sem hífens)

    Args:
        valor (str): Chave aleatória informada

    Returns:
        str: Chave normalizada (lowercase, com hífens)

    Raises:
        ValidationError: Se formato for inválido
    """
    if not valor:
        raise ValidationError('Chave aleatória não pode ser vazia.')

    # Normaliza: remove espaços e converte para minúsculas
    chave_normalizada = valor.strip().lower()

    # Formato com hífens: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX (36 caracteres)
    padrao_com_hifens = r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'

    # Formato sem hífens: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX (32 caracteres)
    padrao_sem_hifens = r'^[a-f0-9]{32}$'

    # Aceita ambos os formatos
    if re.match(padrao_com_hifens, chave_normalizada):
        return chave_normalizada
    elif re.match(padrao_sem_hifens, chave_normalizada):
        # Converte para formato com hífens (padrão UUID)
        chave_com_hifens = f"{chave_normalizada[:8]}-{chave_normalizada[8:12]}-{chave_normalizada[12:16]}-{chave_normalizada[16:20]}-{chave_normalizada[20:]}"
        return chave_com_hifens
    else:
        raise ValidationError(
            'Chave aleatória deve ser um UUID válido (32 caracteres hexadecimais). '
            'Exemplo: 123e4567-e89b-12d3-a456-426614174000'
        )


def validar_chave_pix(tipo_chave, valor):
    """
    Função auxiliar que valida chave PIX baseada no tipo informado.

    Args:
        tipo_chave (str): Tipo da chave (CPF, CNPJ, EMAIL, TELEFONE, ALEATORIA)
        valor (str): Valor da chave a ser validada

    Returns:
        str: Chave validada e normalizada

    Raises:
        ValidationError: Se tipo for inválido ou chave não passar na validação
    """
    validadores = {
        'CPF': validar_cpf_pix,
        'CNPJ': validar_cnpj_pix,
        'EMAIL': validar_email_pix,
        'TELEFONE': validar_telefone_pix,
        'ALEATORIA': validar_chave_aleatoria_pix,
    }

    if tipo_chave not in validadores:
        raise ValidationError(f'Tipo de chave PIX inválido: {tipo_chave}')

    # Executa validador específico
    return validadores[tipo_chave](valor)
