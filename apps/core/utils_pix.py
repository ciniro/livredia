"""
Utilitários para geração de payload e QR Code PIX.

Implementação manual seguindo especificação BR Code do Banco Central do Brasil
(Padrão EMV QR Code para pagamentos instantâneos).

Referências:
- Manual de Padrões para Iniciação do PIX (Banco Central)
- Especificação EMV QR Code
- CRC16-CCITT (polinômio 0x1021)
"""

import base64
import io
import qrcode
import crcmod


def _formatar_campo_tlv(tag, valor):
    """
    Formata um campo no padrão TLV (Tag-Length-Value).

    Args:
        tag (str): Tag de 2 caracteres identificando o campo
        valor (str): Valor do campo

    Returns:
        str: Campo formatado no padrão TLV

    Example:
        _formatar_campo_tlv("00", "01") -> "000201"
        _formatar_campo_tlv("59", "João Silva") -> "59010João Silva"
    """
    tamanho = len(valor)
    return f"{tag}{tamanho:02d}{valor}"


def _calcular_crc16(payload):
    """
    Calcula CRC16-CCITT para payload PIX.

    Utiliza polinômio 0x1021 com valor inicial 0xFFFF conforme
    especificação BR Code do Banco Central.

    Args:
        payload (str): Payload PIX (sem o campo CRC)

    Returns:
        str: CRC16 em hexadecimal maiúsculo (4 caracteres)

    Example:
        _calcular_crc16("00020126...6014BR") -> "A1B2"
    """
    # Configura função CRC16-CCITT (polinômio 0x1021, init 0xFFFF)
    crc16_func = crcmod.mkCrcFun(poly=0x11021, initCrc=0xFFFF, rev=False, xorOut=0x0000)

    # Adiciona placeholder "6304" ao final (tag 63 + length 04)
    payload_com_placeholder = payload + "6304"

    # Calcula CRC sobre o payload completo
    crc_valor = crc16_func(payload_com_placeholder.encode('utf-8'))

    # Retorna em hexadecimal maiúsculo com 4 dígitos
    return f"{crc_valor:04X}"


def gerar_payload_pix(chave_pix, nome_beneficiario, cidade="SAO PAULO", valor=None, descricao=None):
    """
    Gera payload PIX (BR Code) seguindo especificação do Banco Central.

    Implementa estrutura TLV (Tag-Length-Value) conforme padrão EMV QR Code
    para pagamentos instantâneos via PIX.

    Args:
        chave_pix (str): Chave PIX do beneficiário (CPF, CNPJ, email, telefone ou aleatória)
        nome_beneficiario (str): Nome completo do beneficiário (máx. 300 caracteres)
        cidade (str, optional): Cidade do beneficiário. Defaults to "SAO PAULO".
        valor (Decimal, optional): Valor fixo da transação em reais. Se None, valor aberto.
        descricao (str, optional): Descrição/identificador da transação (máx. 25 caracteres)

    Returns:
        str: Payload PIX completo pronto para geração de QR Code

    Raises:
        ValueError: Se descricao exceder 25 caracteres

    Example:
        payload = gerar_payload_pix(
            chave_pix="12345678901",
            nome_beneficiario="João Silva",
            valor=Decimal("10.50"),
            descricao="Doacao Livre Dia"
        )
    """
    # Validações
    if descricao and len(descricao) > 25:
        raise ValueError("Descrição não pode exceder 25 caracteres.")

    # Normaliza nome e cidade (remove acentos, converte para maiúsculas)
    nome_beneficiario = _normalizar_texto(nome_beneficiario)
    cidade = _normalizar_texto(cidade)

    # Inicia construção do payload
    payload = ""

    # 00: Payload Format Indicator (fixo "01")
    payload += _formatar_campo_tlv("00", "01")

    # 01: Point of Initiation Method (OBRIGATÓRIO)
    # "11" = QR Code estático (reutilizável) - múltiplas transações
    # "12" = QR Code dinâmico (uso único) - uma única transação
    # Para doações, sempre usar "11" (estático reutilizável)
    payload += _formatar_campo_tlv("01", "11")

    # 26: Merchant Account Information (informações da conta PIX)
    # Subcampo 00: GUI do PIX (br.gov.bcb.pix)
    # Subcampo 01: Chave PIX
    merchant_account = ""
    merchant_account += _formatar_campo_tlv("00", "br.gov.bcb.pix")
    merchant_account += _formatar_campo_tlv("01", chave_pix)

    # Se houver descrição, adiciona no subcampo 02
    if descricao:
        descricao_normalizada = _normalizar_texto(descricao)
        merchant_account += _formatar_campo_tlv("02", descricao_normalizada)

    payload += _formatar_campo_tlv("26", merchant_account)

    # 52: Merchant Category Code (fixo "0000" para transações pessoa-pessoa)
    payload += _formatar_campo_tlv("52", "0000")

    # 53: Transaction Currency (fixo "986" = Real brasileiro - ISO 4217)
    payload += _formatar_campo_tlv("53", "986")

    # 54: Transaction Amount (opcional - só se valor fixo for definido)
    if valor is not None:
        # Formata valor com 2 casas decimais, sem separadores de milhar
        valor_formatado = f"{float(valor):.2f}"
        payload += _formatar_campo_tlv("54", valor_formatado)

    # 58: Country Code (fixo "BR")
    payload += _formatar_campo_tlv("58", "BR")

    # 59: Merchant Name (nome do beneficiário)
    # Limite máximo: 25 caracteres (especificação EMV QR Code)
    nome_truncado = nome_beneficiario[:25] if len(nome_beneficiario) > 25 else nome_beneficiario
    payload += _formatar_campo_tlv("59", nome_truncado)

    # 60: Merchant City (cidade do beneficiário)
    # Limite máximo: 15 caracteres (especificação EMV QR Code)
    cidade_truncada = cidade[:15] if len(cidade) > 15 else cidade
    payload += _formatar_campo_tlv("60", cidade_truncada)

    # 62: Additional Data Field Template (OBRIGATÓRIO para QR Code estático)
    # Subcampo 05: Transaction ID (txid)
    txid = "***"  # Identificador genérico para QR Code estático
    additional_data = _formatar_campo_tlv("05", txid)
    payload += _formatar_campo_tlv("62", additional_data)

    # 63: CRC16 (calculado sobre todo o payload)
    crc = _calcular_crc16(payload)
    payload += _formatar_campo_tlv("63", crc)

    return payload


def _normalizar_texto(texto):
    """
    Normaliza texto para padrão BR Code (remove acentos, caracteres especiais).

    Args:
        texto (str): Texto a ser normalizado

    Returns:
        str: Texto normalizado (maiúsculas, sem acentos)

    Example:
        _normalizar_texto("João da Silva") -> "JOAO DA SILVA"
        _normalizar_texto("São Paulo") -> "SAO PAULO"
    """
    # Mapeamento de caracteres acentuados para não acentuados
    mapa_acentos = {
        'À': 'A', 'Á': 'A', 'Â': 'A', 'Ã': 'A', 'Ä': 'A',
        'à': 'A', 'á': 'A', 'â': 'A', 'ã': 'A', 'ä': 'A',
        'È': 'E', 'É': 'E', 'Ê': 'E', 'Ë': 'E',
        'è': 'E', 'é': 'E', 'ê': 'E', 'ë': 'E',
        'Ì': 'I', 'Í': 'I', 'Î': 'I', 'Ï': 'I',
        'ì': 'I', 'í': 'I', 'î': 'I', 'ï': 'I',
        'Ò': 'O', 'Ó': 'O', 'Ô': 'O', 'Õ': 'O', 'Ö': 'O',
        'ò': 'O', 'ó': 'O', 'ô': 'O', 'õ': 'O', 'ö': 'O',
        'Ù': 'U', 'Ú': 'U', 'Û': 'U', 'Ü': 'U',
        'ù': 'U', 'ú': 'U', 'û': 'U', 'ü': 'U',
        'Ç': 'C', 'ç': 'C',
        'Ñ': 'N', 'ñ': 'N'
    }

    # Converte para maiúsculas
    texto = texto.upper()

    # Remove acentos
    for acentuado, sem_acento in mapa_acentos.items():
        texto = texto.replace(acentuado, sem_acento)

    # Remove caracteres não permitidos (mantém apenas letras, números e espaços)
    texto_limpo = ''.join(c if c.isalnum() or c.isspace() else '' for c in texto)

    return texto_limpo


def gerar_qrcode_pix_base64(payload, tamanho_box=10, tamanho_borda=4):
    """
    Gera QR Code PIX em formato base64 a partir do payload.

    Cria imagem PNG do QR Code e converte para base64 (data URI)
    para exibição direta em templates HTML.

    Args:
        payload (str): Payload PIX gerado por gerar_payload_pix()
        tamanho_box (int, optional): Tamanho de cada "quadrado" do QR Code. Defaults to 10.
        tamanho_borda (int, optional): Tamanho da borda branca ao redor. Defaults to 4.

    Returns:
        str: String base64 no formato "data:image/png;base64,iVBOR..."

    Example:
        payload = gerar_payload_pix(...)
        qrcode_base64 = gerar_qrcode_pix_base64(payload)
        # No template: <img src="{{ qrcode_base64 }}" alt="QR Code PIX">
    """
    # Cria instância do QR Code
    qr = qrcode.QRCode(
        version=1,  # Tamanho automático (1 = menor possível)
        error_correction=qrcode.constants.ERROR_CORRECT_L,  # Nível L (7% de correção)
        box_size=tamanho_box,  # Tamanho de cada quadrado
        border=tamanho_borda,  # Borda ao redor
    )

    # Adiciona dados do payload
    qr.add_data(payload)
    qr.make(fit=True)

    # Gera imagem PNG
    img = qr.make_image(fill_color="black", back_color="white")

    # Converte para base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    # Retorna como data URI
    return f"data:image/png;base64,{img_base64}"


def gerar_dados_pix_completos(chave_pix, tipo_chave, nome_beneficiario, nome_banco,
                               cidade="SAO PAULO", valor=None, descricao=None):
    """
    Função auxiliar que gera payload E QR Code em uma única chamada.

    Args:
        chave_pix (str): Chave PIX do beneficiário
        tipo_chave (str): Tipo da chave (CPF, CNPJ, EMAIL, TELEFONE, ALEATORIA)
        nome_beneficiario (str): Nome completo do beneficiário
        nome_banco (str): Nome do banco (para exibição, não usado no payload)
        cidade (str, optional): Cidade do beneficiário. Defaults to "SAO PAULO".
        valor (Decimal, optional): Valor fixo da transação. Defaults to None.
        descricao (str, optional): Descrição da transação. Defaults to None.

    Returns:
        dict: Dicionário com 'payload', 'qrcode_base64', 'tipo_chave', 'nome_banco'

    Example:
        dados = gerar_dados_pix_completos(
            chave_pix="usuario@email.com",
            tipo_chave="EMAIL",
            nome_beneficiario="João Silva",
            nome_banco="Banco do Brasil",
            valor=Decimal("25.00")
        )
        # Template pode acessar: dados['qrcode_base64'], dados['payload']
    """
    # Gera payload
    payload = gerar_payload_pix(
        chave_pix=chave_pix,
        nome_beneficiario=nome_beneficiario,
        cidade=cidade,
        valor=valor,
        descricao=descricao
    )

    # Gera QR Code
    qrcode_base64 = gerar_qrcode_pix_base64(payload)

    return {
        'payload': payload,
        'qrcode_base64': qrcode_base64,
        'tipo_chave': tipo_chave,
        'nome_banco': nome_banco,
        'chave_pix': chave_pix,
        'valor': valor
    }
