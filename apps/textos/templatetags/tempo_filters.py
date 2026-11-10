"""
Template tags/filters para formatação de tempo de leitura.
"""
from django import template

register = template.Library()


@register.filter(name='formatar_tempo')
def formatar_tempo(segundos):
    """
    Formata tempo de leitura em formato humano.

    Formato:
    - None ou 0: "0s"
    - Menos de 1 minuto: "45s"
    - Menos de 1 hora: "23min"
    - 1 hora ou mais: "14h 55min"

    Uso no template:
    {{ texto.tempo_total_leitura|formatar_tempo }}
    """
    if not segundos or segundos <= 0:
        return "0s"

    segundos = int(segundos)
    horas = segundos // 3600
    minutos = (segundos % 3600) // 60
    segundos_restantes = segundos % 60

    if horas > 0:
        return f"{horas}h {minutos}min"
    elif minutos > 0:
        return f"{minutos}min"
    else:
        return f"{segundos_restantes}s"


@register.filter(name='calcular_tempo_medio')
def calcular_tempo_medio(tempo_total, visualizacoes_unicas):
    """
    Calcula e formata o tempo médio de leitura.

    Tempo médio = tempo_total ÷ visualizacoes_unicas

    Uso no template:
    {{ texto.tempo_total_leitura|calcular_tempo_medio:texto.visualizacoes_unicas }}
    """
    if not tempo_total or not visualizacoes_unicas or visualizacoes_unicas == 0:
        return "0s"

    tempo_medio_segundos = int(tempo_total) // int(visualizacoes_unicas)
    return formatar_tempo(tempo_medio_segundos)


@register.filter(name='periodo_do_dia')
def periodo_do_dia(data_hora):
    """
    Retorna o período do dia baseado na hora.

    Períodos:
    - Madrugada: 00:00 - 05:59
    - Manhã: 06:00 - 11:59
    - Tarde: 12:00 - 17:59
    - Noite: 18:00 - 23:59

    Uso no template:
    {{ texto.data_publicacao|periodo_do_dia }}
    """
    if not data_hora:
        return ""

    hora = data_hora.hour

    if 0 <= hora < 6:
        return "madrugada"
    elif 6 <= hora < 12:
        return "manhã"
    elif 12 <= hora < 18:
        return "tarde"
    else:  # 18 <= hora < 24
        return "noite"
