"""Adesivos de conquista (gamificação), como função pura: fácil de testar e de explicar.

Ideia: além do ranking (que COMPARA alunos e pode desmotivar quem fica embaixo), os
adesivos premiam o PROGRESSO de cada um, cada aluno contra si mesmo. Como as figurinhas
coladas num caderno, combinando com a identidade visual do MatIF.

Nada é guardado no banco: tudo é calculado a partir das respostas (e da data em que o
questionário de estilos foi concluído). Assim não há dado pessoal novo (LGPD) e mudar
uma regra vale na hora, inclusive para conquistas antigas.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from .gamificacao import dia_local


@dataclass(frozen=True)
class RespostaSimples:
    exercicio_id: int
    correta: bool
    pontos_ganhos: int          # > 0 só quando acertou DE PRIMEIRA (regra dos pontos)
    respondida_em: datetime


# (id, título, como ganhar, meta). A ordem é a ordem em que aparecem no caderno.
ADESIVOS = [
    ("primeiro_acerto", "Primeiro acerto", "Acerte seu primeiro exercício.", 1),
    ("na_primeira", "Na primeira!", "Acerte 5 exercícios de primeira.", 5),
    ("dez_na_conta", "Dez na conta", "Acerte 10 exercícios diferentes.", 10),
    ("nao_desisto", "Não desisto", "Acerte um exercício que você tinha errado antes.", 1),
    ("modulo_fechado", "Módulo fechado", "Acerte todos os exercícios de um módulo.", 1),
    ("tres_dias", "Três dias seguidos", "Responda exercícios em 3 dias seguidos.", 3),
    ("semana_firme", "Uma semana firme", "Responda exercícios em 7 dias seguidos.", 7),
    ("me_conheco", "Me conheço", "Descubra seu estilo de aprendizagem.", 1),
]


def calcular_conquistas(respostas: list[RespostaSimples], modulos: dict[int, set[int]],
                        estilo_concluido_em: datetime | None) -> list[dict]:
    """Devolve, para cada adesivo: id, titulo, descricao, meta, progresso, ganho, ganho_em.

    respostas : todas as respostas do aluno (qualquer ordem)
    modulos   : {módulo: {exercícios}} dos módulos das salas em que o aluno está
    """
    progresso = {i: 0 for i, *_ in ADESIVOS}
    ganho_em: dict[str, datetime] = {}

    def marcar(chave: str, valor: int, quando: datetime) -> None:
        progresso[chave] = max(progresso[chave], valor)
        meta = next(m for i, _, _, m in ADESIVOS if i == chave)
        if valor >= meta and chave not in ganho_em:
            ganho_em[chave] = quando

    acertados: set[int] = set()
    errados: set[int] = set()
    de_primeira = 0
    for r in sorted(respostas, key=lambda r: r.respondida_em):
        if r.correta:
            if r.exercicio_id in errados:                       # errou antes e agora acertou
                marcar("nao_desisto", 1, r.respondida_em)
            acertados.add(r.exercicio_id)
            de_primeira += r.pontos_ganhos > 0
            marcar("primeiro_acerto", len(acertados), r.respondida_em)
            marcar("dez_na_conta", len(acertados), r.respondida_em)
            marcar("na_primeira", de_primeira, r.respondida_em)
            if any(ex and ex <= acertados for ex in modulos.values()):
                marcar("modulo_fechado", 1, r.respondida_em)
        else:
            errados.add(r.exercicio_id)

    # dias seguidos (no fuso de Brasília, como o streak)
    seq, anterior = 0, None
    for dia in sorted({dia_local(r.respondida_em) for r in respostas}):
        seq = seq + 1 if anterior is not None and dia - anterior == timedelta(days=1) else 1
        anterior = dia
        quando = datetime(dia.year, dia.month, dia.day)
        marcar("tres_dias", seq, quando)
        marcar("semana_firme", seq, quando)

    if estilo_concluido_em is not None:
        marcar("me_conheco", 1, estilo_concluido_em)

    return [{"id": i, "titulo": t, "descricao": d, "meta": m, "progresso": min(progresso[i], m),
             "ganho": i in ganho_em, "ganho_em": ganho_em.get(i)} for i, t, d, m in ADESIVOS]
