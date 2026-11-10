"""
Serviços do Vilarejo Literário

Gerencia a lógica de negócio do vilarejo, incluindo:
- Obtenção/criação de vilarejos
- Cálculo de vizinhos (com banimentos e moradores permanentes)
- Gestão de mensagens
"""

from django.db import transaction
from django.db.models import Q
from apps.usuarios.utils_vizinhos import buscar_vizinhos, calcular_similaridade
from .models import (
    Vilarejo, MensagemVilarejo, MoradorPermanente,
    BanimentoVilarejo, HistoricoCondominio, HistoricoVizinho
)


def obter_ou_criar_vilarejo(usuario):
    """
    Obtém o vilarejo de um usuário ou cria um novo se não existir.

    Args:
        usuario: Usuário dono do vilarejo

    Returns:
        Vilarejo: O vilarejo do usuário
    """
    vilarejo, criado = Vilarejo.objects.get_or_create(
        dono=usuario,
        defaults={'nome': f'Vilarejo de {usuario.get_display_name()}'}
    )
    return vilarejo


def obter_vizinhos_vilarejo(vilarejo, limite=9):
    """
    Obtém os vizinhos do vilarejo, aplicando regras de banimento e moradores permanentes.

    Regras:
    1. Busca vizinhos por similaridade (função existente)
    2. Remove usuários banidos (banimento mútuo)
    3. Adiciona moradores permanentes que não estão na lista
    4. Registra histórico de vizinhos para convites futuros

    Args:
        vilarejo: O vilarejo
        limite: Número máximo de vizinhos (padrão 9)

    Returns:
        list: Lista de dicionários com 'usuario', 'similaridade', 'is_morador_permanente'
    """
    dono = vilarejo.dono

    # 1. Obter IDs dos usuários banidos (banimento mútuo)
    banidos_pelo_dono = set(
        BanimentoVilarejo.objects.filter(vilarejo=vilarejo)
        .values_list('usuario_banido_id', flat=True)
    )

    # Usuários que baniram o dono (banimento mútuo)
    vilarejos_que_baniram_dono = Vilarejo.objects.filter(
        banimentos__usuario_banido=dono
    ).values_list('dono_id', flat=True)
    banidos_mutuos = banidos_pelo_dono | set(vilarejos_que_baniram_dono)

    # 2. Obter moradores permanentes
    moradores_permanentes = set(
        MoradorPermanente.objects.filter(vilarejo=vilarejo)
        .values_list('usuario_id', flat=True)
    )

    # 3. Buscar vizinhos por similaridade (excluindo banidos)
    vizinhos_raw = buscar_vizinhos(dono, limite=limite + len(banidos_mutuos) + 10)

    # Filtrar banidos e preparar resultado
    vizinhos_filtrados = []
    usuarios_adicionados = set()

    for v in vizinhos_raw:
        usuario = v['usuario']
        if usuario.id not in banidos_mutuos and usuario.id not in usuarios_adicionados:
            vizinhos_filtrados.append({
                'usuario': usuario,
                'similaridade': v['similaridade'],
                'is_morador_permanente': usuario.id in moradores_permanentes
            })
            usuarios_adicionados.add(usuario.id)

            # Registrar no histórico de vizinhos (para convites futuros)
            HistoricoVizinho.objects.get_or_create(
                vilarejo=vilarejo,
                usuario=usuario
            )

            if len(vizinhos_filtrados) >= limite:
                break

    # 4. Adicionar moradores permanentes que não estão na lista de vizinhos atuais
    for morador_id in moradores_permanentes:
        if morador_id not in usuarios_adicionados and morador_id not in banidos_mutuos:
            from apps.usuarios.models import User
            try:
                morador = User.objects.get(id=morador_id, is_active=True)
                similaridade = calcular_similaridade(dono, morador)
                vizinhos_filtrados.append({
                    'usuario': morador,
                    'similaridade': similaridade,
                    'is_morador_permanente': True
                })
                usuarios_adicionados.add(morador_id)
            except User.DoesNotExist:
                pass

    # Ordenar por similaridade (moradores permanentes mantêm posição)
    vizinhos_filtrados.sort(key=lambda x: x['similaridade'], reverse=True)

    return vizinhos_filtrados


def verificar_acesso_vilarejo(usuario, vilarejo):
    """
    Verifica se um usuário tem acesso a um vilarejo.

    Regras de acesso:
    1. Dono sempre tem acesso
    2. Admin (role=ADMIN) sempre tem acesso
    3. Vizinhos atuais têm acesso
    4. Moradores permanentes têm acesso
    5. Usuários banidos NÃO têm acesso

    Args:
        usuario: Usuário tentando acessar
        vilarejo: Vilarejo a ser acessado

    Returns:
        tuple: (tem_acesso: bool, motivo: str, tipo_acesso: str)
    """
    # Dono sempre tem acesso
    if vilarejo.dono_id == usuario.id:
        return True, None, 'dono'

    # Admin sempre tem acesso
    if usuario.role == 'ADMIN':
        return True, None, 'admin'

    # Verificar banimento mútuo
    # O dono baniu este usuário?
    if BanimentoVilarejo.objects.filter(vilarejo=vilarejo, usuario_banido=usuario).exists():
        return False, 'Você foi banido deste vilarejo.', None

    # Este usuário baniu o dono?
    try:
        vilarejo_usuario = Vilarejo.objects.get(dono=usuario)
        if BanimentoVilarejo.objects.filter(vilarejo=vilarejo_usuario, usuario_banido=vilarejo.dono).exists():
            return False, 'Você não pode acessar este vilarejo.', None
    except Vilarejo.DoesNotExist:
        pass

    # Verificar se é morador permanente
    if MoradorPermanente.objects.filter(vilarejo=vilarejo, usuario=usuario).exists():
        return True, None, 'morador_permanente'

    # Verificar se é vizinho atual
    # A lógica correta é: o dono do vilarejo deve ser vizinho do usuário
    # (o usuário pode acessar vilarejos de seus vizinhos)
    vizinhos_usuario = buscar_vizinhos(usuario, limite=20)
    for v in vizinhos_usuario:
        if v['usuario'].id == vilarejo.dono_id:
            return True, None, 'vizinho'

    return False, 'Você não tem acesso a este vilarejo.', None


def criar_mensagem(vilarejo, autor, conteudo):
    """
    Cria uma mensagem no vilarejo.

    Args:
        vilarejo: Vilarejo onde a mensagem será postada
        autor: Usuário que está enviando a mensagem
        conteudo: Texto da mensagem (máx 500 caracteres)

    Returns:
        MensagemVilarejo: A mensagem criada

    Raises:
        ValueError: Se o conteúdo for inválido
    """
    conteudo = conteudo.strip()

    if not conteudo:
        raise ValueError('A mensagem não pode ser vazia.')

    if len(conteudo) > 500:
        raise ValueError('A mensagem não pode ter mais de 500 caracteres.')

    with transaction.atomic():
        mensagem = MensagemVilarejo.objects.create(
            vilarejo=vilarejo,
            autor=autor,
            conteudo=conteudo
        )

        # Aplicar limite FIFO de 2000 mensagens
        aplicar_limite_mensagens(vilarejo)

    return mensagem


def aplicar_limite_mensagens(vilarejo, limite=2000):
    """
    Aplica o limite FIFO de mensagens no vilarejo.
    Remove as mensagens mais antigas se o limite for excedido.

    Args:
        vilarejo: Vilarejo
        limite: Número máximo de mensagens (padrão 2000)
    """
    total_mensagens = MensagemVilarejo.objects.filter(vilarejo=vilarejo).count()

    if total_mensagens > limite:
        excesso = total_mensagens - limite
        # Pegar IDs das mensagens mais antigas para deletar
        ids_para_deletar = list(
            MensagemVilarejo.objects.filter(vilarejo=vilarejo)
            .order_by('criado_em')
            .values_list('id', flat=True)[:excesso]
        )
        MensagemVilarejo.objects.filter(id__in=ids_para_deletar).delete()


def obter_mensagens(vilarejo, limite=50, antes_de=None):
    """
    Obtém mensagens do vilarejo com paginação.

    Args:
        vilarejo: Vilarejo
        limite: Número de mensagens a retornar
        antes_de: ID da mensagem para paginação (mensagens anteriores a esta)

    Returns:
        QuerySet: Mensagens ordenadas por data (mais antigas primeiro)
    """
    queryset = MensagemVilarejo.objects.filter(vilarejo=vilarejo)

    if antes_de:
        queryset = queryset.filter(id__lt=antes_de)

    # Pegar as últimas N mensagens (mais recentes), depois inverter para exibir em ordem cronológica
    mensagens = list(queryset.order_by('-criado_em')[:limite])
    mensagens.reverse()

    return mensagens


def extrair_mencoes(conteudo):
    """
    Extrai menções @usuario do conteúdo da mensagem.

    Args:
        conteudo: Texto da mensagem

    Returns:
        list: Lista de usernames mencionados
    """
    import re
    # Padrão: @ seguido de caracteres alfanuméricos, underscores ou hífens
    pattern = r'@([a-zA-Z0-9_-]+)'
    mencoes = re.findall(pattern, conteudo)
    return list(set(mencoes))  # Remover duplicatas


# =============================================================================
# SERVIÇOS DE GESTÃO DO VILAREJO (Fase 3)
# =============================================================================

def convidar_morador_permanente(vilarejo, usuario_convidado, convidado_por):
    """
    Convida um usuário para ser morador permanente do vilarejo.

    Regras:
    - Apenas o dono do vilarejo pode convidar
    - Usuário deve ter sido vizinho pelo menos uma vez (estar no histórico)
    - Não pode convidar usuários banidos
    - Não pode convidar quem já é morador permanente

    Args:
        vilarejo: Vilarejo
        usuario_convidado: Usuário a ser convidado
        convidado_por: Usuário que está convidando (deve ser o dono)

    Returns:
        MoradorPermanente: O registro criado

    Raises:
        PermissionError: Se não tiver permissão
        ValueError: Se o convite for inválido
    """
    # Verificar permissão
    if vilarejo.dono_id != convidado_por.id:
        raise PermissionError('Apenas o dono do vilarejo pode convidar moradores permanentes.')

    # Verificar se já é morador permanente
    if MoradorPermanente.objects.filter(vilarejo=vilarejo, usuario=usuario_convidado).exists():
        raise ValueError('Este usuário já é morador permanente.')

    # Verificar se foi banido
    if BanimentoVilarejo.objects.filter(vilarejo=vilarejo, usuario_banido=usuario_convidado).exists():
        raise ValueError('Não é possível convidar um usuário banido.')

    # Verificar se o usuário convidado baniu o dono (banimento mútuo)
    try:
        vilarejo_convidado = Vilarejo.objects.get(dono=usuario_convidado)
        if BanimentoVilarejo.objects.filter(vilarejo=vilarejo_convidado, usuario_banido=vilarejo.dono).exists():
            raise ValueError('Não é possível convidar este usuário.')
    except Vilarejo.DoesNotExist:
        pass

    # Verificar se foi vizinho (está no histórico)
    if not HistoricoVizinho.objects.filter(vilarejo=vilarejo, usuario=usuario_convidado).exists():
        raise ValueError('Só é possível convidar usuários que já foram seus vizinhos.')

    with transaction.atomic():
        morador = MoradorPermanente.objects.create(
            vilarejo=vilarejo,
            usuario=usuario_convidado,
            convidado_por=convidado_por
        )

        # Registrar no histórico do condomínio
        HistoricoCondominio.objects.create(
            vilarejo=vilarejo,
            tipo_evento='MORADOR_ADICIONADO',
            usuario_alvo=usuario_convidado,
            realizado_por=convidado_por,
            detalhes=f'{usuario_convidado.get_display_name()} foi convidado como morador permanente.'
        )

    return morador


def remover_morador_permanente(vilarejo, usuario_removido, removido_por):
    """
    Remove um morador permanente do vilarejo.

    Args:
        vilarejo: Vilarejo
        usuario_removido: Usuário a ser removido
        removido_por: Usuário que está removendo (deve ser o dono)

    Raises:
        PermissionError: Se não tiver permissão
        ValueError: Se o usuário não for morador permanente
    """
    # Verificar permissão
    if vilarejo.dono_id != removido_por.id:
        raise PermissionError('Apenas o dono do vilarejo pode remover moradores permanentes.')

    try:
        morador = MoradorPermanente.objects.get(vilarejo=vilarejo, usuario=usuario_removido)
    except MoradorPermanente.DoesNotExist:
        raise ValueError('Este usuário não é morador permanente.')

    with transaction.atomic():
        morador.delete()

        # Registrar no histórico do condomínio
        HistoricoCondominio.objects.create(
            vilarejo=vilarejo,
            tipo_evento='MORADOR_REMOVIDO',
            usuario_alvo=usuario_removido,
            realizado_por=removido_por,
            detalhes=f'{usuario_removido.get_display_name()} foi removido dos moradores permanentes.'
        )


def banir_usuario(vilarejo, usuario_banido, banido_por, motivo=''):
    """
    Bane um usuário do vilarejo.

    O banimento é mútuo: se A bane B, B também não pode acessar o vilarejo de A,
    e A não pode acessar o vilarejo de B.

    Args:
        vilarejo: Vilarejo
        usuario_banido: Usuário a ser banido
        banido_por: Usuário que está banindo (deve ser dono ou admin)
        motivo: Motivo do banimento (opcional)

    Returns:
        BanimentoVilarejo: O registro criado

    Raises:
        PermissionError: Se não tiver permissão
        ValueError: Se o banimento for inválido
    """
    # Verificar permissão (dono ou admin)
    is_dono = vilarejo.dono_id == banido_por.id
    is_admin = banido_por.role == 'ADMIN'

    if not (is_dono or is_admin):
        raise PermissionError('Apenas o dono do vilarejo ou um admin pode banir usuários.')

    # Não pode banir a si mesmo
    if usuario_banido.id == banido_por.id:
        raise ValueError('Você não pode banir a si mesmo.')

    # Não pode banir o dono
    if usuario_banido.id == vilarejo.dono_id:
        raise ValueError('Não é possível banir o dono do vilarejo.')

    # Verificar se já está banido
    if BanimentoVilarejo.objects.filter(vilarejo=vilarejo, usuario_banido=usuario_banido).exists():
        raise ValueError('Este usuário já está banido.')

    with transaction.atomic():
        banimento = BanimentoVilarejo.objects.create(
            vilarejo=vilarejo,
            usuario_banido=usuario_banido,
            banido_por=banido_por,
            motivo=motivo
        )

        # Se era morador permanente, remover também
        MoradorPermanente.objects.filter(vilarejo=vilarejo, usuario=usuario_banido).delete()

        # Registrar no histórico do condomínio
        HistoricoCondominio.objects.create(
            vilarejo=vilarejo,
            tipo_evento='USUARIO_BANIDO',
            usuario_alvo=usuario_banido,
            realizado_por=banido_por,
            detalhes=f'{usuario_banido.get_display_name()} foi banido. Motivo: {motivo or "Não informado"}'
        )

    return banimento


def desbanir_usuario(vilarejo, usuario_desbanido, desbanido_por):
    """
    Remove o banimento de um usuário.

    Args:
        vilarejo: Vilarejo
        usuario_desbanido: Usuário a ser desbanido
        desbanido_por: Usuário que está desbanindo (deve ser dono ou admin)

    Raises:
        PermissionError: Se não tiver permissão
        ValueError: Se o usuário não estiver banido
    """
    # Verificar permissão (dono ou admin)
    is_dono = vilarejo.dono_id == desbanido_por.id
    is_admin = desbanido_por.role == 'ADMIN'

    if not (is_dono or is_admin):
        raise PermissionError('Apenas o dono do vilarejo ou um admin pode desbanir usuários.')

    try:
        banimento = BanimentoVilarejo.objects.get(vilarejo=vilarejo, usuario_banido=usuario_desbanido)
    except BanimentoVilarejo.DoesNotExist:
        raise ValueError('Este usuário não está banido.')

    with transaction.atomic():
        banimento.delete()

        # Registrar no histórico do condomínio
        HistoricoCondominio.objects.create(
            vilarejo=vilarejo,
            tipo_evento='USUARIO_DESBANIDO',
            usuario_alvo=usuario_desbanido,
            realizado_por=desbanido_por,
            detalhes=f'{usuario_desbanido.get_display_name()} teve o banimento removido.'
        )


def alterar_nome_vilarejo(vilarejo, novo_nome, alterado_por):
    """
    Altera o nome do vilarejo.

    Args:
        vilarejo: Vilarejo
        novo_nome: Novo nome (máx 100 caracteres)
        alterado_por: Usuário que está alterando (deve ser o dono)

    Raises:
        PermissionError: Se não tiver permissão
        ValueError: Se o nome for inválido
    """
    if vilarejo.dono_id != alterado_por.id:
        raise PermissionError('Apenas o dono pode alterar o nome do vilarejo.')

    novo_nome = novo_nome.strip()

    if not novo_nome:
        raise ValueError('O nome não pode ser vazio.')

    if len(novo_nome) > 100:
        raise ValueError('O nome não pode ter mais de 100 caracteres.')

    nome_antigo = vilarejo.nome

    with transaction.atomic():
        vilarejo.nome = novo_nome
        vilarejo.save()

        # Registrar no histórico do condomínio
        HistoricoCondominio.objects.create(
            vilarejo=vilarejo,
            tipo_evento='NOME_ALTERADO',
            realizado_por=alterado_por,
            detalhes=f'Nome alterado de "{nome_antigo}" para "{novo_nome}".'
        )


def obter_historico_condominio(vilarejo, limite=50):
    """
    Obtém o histórico do condomínio (últimas ações administrativas).

    Args:
        vilarejo: Vilarejo
        limite: Número de registros a retornar

    Returns:
        QuerySet: Registros do histórico ordenados por data (mais recentes primeiro)
    """
    return HistoricoCondominio.objects.filter(vilarejo=vilarejo).order_by('-data')[:limite]


def obter_moradores_permanentes(vilarejo):
    """
    Obtém a lista de moradores permanentes do vilarejo.

    Args:
        vilarejo: Vilarejo

    Returns:
        QuerySet: Moradores permanentes
    """
    return MoradorPermanente.objects.filter(vilarejo=vilarejo).select_related('usuario', 'convidado_por')


def obter_usuarios_banidos(vilarejo):
    """
    Obtém a lista de usuários banidos do vilarejo.

    Args:
        vilarejo: Vilarejo

    Returns:
        QuerySet: Banimentos
    """
    return BanimentoVilarejo.objects.filter(vilarejo=vilarejo).select_related('usuario_banido', 'banido_por')


def obter_historico_vizinhos(vilarejo):
    """
    Obtém o histórico de todos os usuários que já foram vizinhos.
    Usado para listar candidatos a moradores permanentes.

    Args:
        vilarejo: Vilarejo

    Returns:
        QuerySet: Histórico de vizinhos
    """
    # IDs de moradores permanentes e banidos (para excluir da lista de candidatos)
    moradores_ids = set(
        MoradorPermanente.objects.filter(vilarejo=vilarejo).values_list('usuario_id', flat=True)
    )
    banidos_ids = set(
        BanimentoVilarejo.objects.filter(vilarejo=vilarejo).values_list('usuario_banido_id', flat=True)
    )

    excluir_ids = moradores_ids | banidos_ids | {vilarejo.dono_id}

    return HistoricoVizinho.objects.filter(
        vilarejo=vilarejo
    ).exclude(
        usuario_id__in=excluir_ids
    ).select_related('usuario').order_by('-primeira_vez_vizinho')


def obter_vilarejos_usuario(usuario):
    """
    Obtém todos os vilarejos que um usuário tem acesso.

    Inclui:
    1. Vilarejo próprio (onde é dono)
    2. Vilarejos onde é morador permanente
    3. Vilarejos onde é vizinho atual (por similaridade)

    Args:
        usuario: Usuário

    Returns:
        list: Lista de dicionários com informações do vilarejo e tipo de acesso
    """
    vilarejos_result = []
    vilarejos_ids_adicionados = set()

    # 1. Vilarejo próprio
    try:
        vilarejo_proprio = Vilarejo.objects.select_related('dono').get(dono=usuario)
        vilarejos_result.append({
            'vilarejo': vilarejo_proprio,
            'anfitriao': vilarejo_proprio.dono,
            'similaridade': 100,  # 100% consigo mesmo
            'tipo_acesso': 'dono'
        })
        vilarejos_ids_adicionados.add(vilarejo_proprio.id)
    except Vilarejo.DoesNotExist:
        pass

    # 2. Vilarejos onde é morador permanente
    morador_em = MoradorPermanente.objects.filter(
        usuario=usuario
    ).select_related('vilarejo', 'vilarejo__dono')

    for morador in morador_em:
        vilarejo = morador.vilarejo
        if vilarejo.id not in vilarejos_ids_adicionados:
            # Verificar banimento mútuo
            if not BanimentoVilarejo.objects.filter(vilarejo=vilarejo, usuario_banido=usuario).exists():
                similaridade = calcular_similaridade(usuario, vilarejo.dono)
                vilarejos_result.append({
                    'vilarejo': vilarejo,
                    'anfitriao': vilarejo.dono,
                    'similaridade': similaridade,
                    'tipo_acesso': 'morador_permanente'
                })
                vilarejos_ids_adicionados.add(vilarejo.id)

    # 3. Vilarejos onde é vizinho atual (por similaridade)
    # Buscar vizinhos do usuário - eles têm vilarejos que o usuário pode acessar
    vizinhos_raw = buscar_vizinhos(usuario, limite=20)

    for v in vizinhos_raw:
        vizinho = v['usuario']
        try:
            vilarejo_vizinho = Vilarejo.objects.select_related('dono').get(dono=vizinho)
            if vilarejo_vizinho.id not in vilarejos_ids_adicionados:
                # Verificar se não está banido
                if not BanimentoVilarejo.objects.filter(vilarejo=vilarejo_vizinho, usuario_banido=usuario).exists():
                    # Verificar se o usuário não baniu o dono do vilarejo
                    try:
                        vilarejo_usuario = Vilarejo.objects.get(dono=usuario)
                        if BanimentoVilarejo.objects.filter(vilarejo=vilarejo_usuario, usuario_banido=vizinho).exists():
                            continue  # Banimento mútuo
                    except Vilarejo.DoesNotExist:
                        pass

                    vilarejos_result.append({
                        'vilarejo': vilarejo_vizinho,
                        'anfitriao': vilarejo_vizinho.dono,
                        'similaridade': v['similaridade'],
                        'tipo_acesso': 'vizinho'
                    })
                    vilarejos_ids_adicionados.add(vilarejo_vizinho.id)
        except Vilarejo.DoesNotExist:
            pass

    # Ordenar por similaridade (descendente)
    vilarejos_result.sort(key=lambda x: x['similaridade'], reverse=True)

    return vilarejos_result
