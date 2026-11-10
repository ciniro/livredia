"""
Utilitários para cálculo de similaridade entre usuários (Item 5 ROADMAP)

Fórmula ponderada:
- 40% - Autores seguidos em comum
- 30% - Textos favoritos em comum
- 20% - Cartões de biblioteca assinados em comum
- 10% - Textos marcados como lidos em comum

Score final: 0 a 100
"""

from apps.usuarios.models import User, AutorSeguido
from apps.textos.models import TextoFavorito, CartaoBiblioteca, TextoLido


def calcular_similaridade(usuario_base, usuario_comparado):
    """
    Calcula a similaridade entre dois usuários.

    Args:
        usuario_base: User que é a referência
        usuario_comparado: User que será comparado

    Returns:
        float: Score de similaridade de 0 a 100
    """
    # Pesos conforme especificação
    PESO_AUTORES = 40
    PESO_FAVORITOS = 30
    PESO_CARTOES = 20
    PESO_LIDOS = 10

    score = 0.0

    # 1. Autores seguidos em comum (40%)
    autores_base = set(
        AutorSeguido.objects.filter(seguidor=usuario_base)
        .values_list('autor_id', flat=True)
    )
    autores_comparado = set(
        AutorSeguido.objects.filter(seguidor=usuario_comparado)
        .values_list('autor_id', flat=True)
    )

    if autores_base or autores_comparado:
        autores_comum = autores_base & autores_comparado
        autores_total = autores_base | autores_comparado
        if autores_total:
            score += PESO_AUTORES * (len(autores_comum) / len(autores_total))

    # 2. Textos favoritos em comum (30%)
    favoritos_base = set(
        TextoFavorito.objects.filter(usuario=usuario_base)
        .values_list('texto_id', flat=True)
    )
    favoritos_comparado = set(
        TextoFavorito.objects.filter(usuario=usuario_comparado)
        .values_list('texto_id', flat=True)
    )

    if favoritos_base or favoritos_comparado:
        favoritos_comum = favoritos_base & favoritos_comparado
        favoritos_total = favoritos_base | favoritos_comparado
        if favoritos_total:
            score += PESO_FAVORITOS * (len(favoritos_comum) / len(favoritos_total))

    # 3. Cartões de biblioteca assinados em comum (20%)
    cartoes_base = set(
        CartaoBiblioteca.objects.filter(usuario=usuario_base)
        .values_list('texto_id', flat=True)
    )
    cartoes_comparado = set(
        CartaoBiblioteca.objects.filter(usuario=usuario_comparado)
        .values_list('texto_id', flat=True)
    )

    if cartoes_base or cartoes_comparado:
        cartoes_comum = cartoes_base & cartoes_comparado
        cartoes_total = cartoes_base | cartoes_comparado
        if cartoes_total:
            score += PESO_CARTOES * (len(cartoes_comum) / len(cartoes_total))

    # 4. Textos marcados como lidos em comum (10%)
    lidos_base = set(
        TextoLido.objects.filter(usuario=usuario_base)
        .values_list('texto_id', flat=True)
    )
    lidos_comparado = set(
        TextoLido.objects.filter(usuario=usuario_comparado)
        .values_list('texto_id', flat=True)
    )

    if lidos_base or lidos_comparado:
        lidos_comum = lidos_base & lidos_comparado
        lidos_total = lidos_base | lidos_comparado
        if lidos_total:
            score += PESO_LIDOS * (len(lidos_comum) / len(lidos_total))

    return round(score, 1)


def buscar_vizinhos(usuario, limite=9):
    """
    Busca os vizinhos mais similares de um usuário.

    Args:
        usuario: User para quem buscar vizinhos
        limite: Número máximo de vizinhos a retornar (padrão: 6)

    Returns:
        list: Lista de dicts com {usuario, similaridade}
              Ordenada por similaridade decrescente
    """
    # Buscar todos os usuários ativos (exceto o próprio e clássicos)
    # Inclui usuários com perfil privado no cálculo de similaridade
    # select_related('vilarejo') para evitar N+1 queries ao exibir botão de visitar
    candidatos = User.objects.filter(
        is_active=True,
        is_classico=False
    ).exclude(id=usuario.id).select_related('vilarejo')

    # Calcular similaridade com cada candidato
    vizinhos = []
    for candidato in candidatos:
        similaridade = calcular_similaridade(usuario, candidato)

        # Só incluir se tiver alguma similaridade
        if similaridade > 0:
            vizinhos.append({
                'usuario': candidato,
                'similaridade': similaridade
            })

    # Ordenar por similaridade decrescente e limitar
    vizinhos.sort(key=lambda x: x['similaridade'], reverse=True)

    return vizinhos[:limite]
