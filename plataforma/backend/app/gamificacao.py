"""Regras de gamificação, como funções puras (fáceis de testar e de explicar).

PONTOS: cada exercício vale `pontos` (padrão 10), ganhos só se a PRIMEIRA
tentativa do aluno naquele exercício estiver certa. Depois de responder, o
aluno vê a alternativa correta e a explicação (feedback imediato ajuda a
aprender) e pode refazer o exercício, mas refazer não rende pontos — senão
bastaria errar de propósito, ver a resposta e acertar em seguida.

STREAK (sequência): nº de dias SEGUIDOS em que o aluno respondeu pelo menos um
exercício, contados no fuso de Brasília. A sequência atual continua viva se o
último dia de atividade foi hoje ou ontem (o aluno ainda pode estudar hoje).

RANKING: por sala, soma dos pontos ganhos nos exercícios dos módulos daquela
sala; em caso de empate, ordem alfabética. Para os colegas, o nome aparece
abreviado ("Ana L."); o professor vê o nome completo.
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")


def dia_local(momento: datetime) -> date:
    """Data no fuso de Brasília. Datas sem fuso são tratadas como UTC (o SQLite perde o fuso)."""
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=ZoneInfo("UTC"))
    return momento.astimezone(FUSO).date()


def calcular_streak(momentos: list[datetime], hoje: date) -> tuple[int, int]:
    """Devolve (sequência atual, maior sequência) a partir dos horários das respostas."""
    dias = sorted({dia_local(m) for m in momentos})
    if not dias:
        return 0, 0
    melhor = atual = 1
    for anterior, dia in zip(dias, dias[1:]):
        atual = atual + 1 if dia - anterior == timedelta(days=1) else 1
        melhor = max(melhor, atual)
    viva = (hoje - dias[-1]) <= timedelta(days=1)
    return (atual if viva else 0), melhor


def nome_curto(nome: str) -> str:
    """'Ana Souza Lima' -> 'Ana L.' (ranking visível aos colegas com o mínimo de dados)."""
    partes = nome.split()
    return partes[0] if len(partes) == 1 else f"{partes[0]} {partes[-1][0]}."
