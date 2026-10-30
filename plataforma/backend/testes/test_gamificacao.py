"""Testes das regras de gamificação (funções puras) e do ranking."""

from datetime import date, datetime, timezone

from app.gamificacao import calcular_streak, dia_local, nome_curto
from testes.conftest import registrar


def _utc(a, m, d, h=15):
    return datetime(a, m, d, h, tzinfo=timezone.utc)


def test_streak():
    hoje = date(2026, 11, 10)
    assert calcular_streak([], hoje) == (0, 0)
    seguidos = [_utc(2026, 11, d) for d in (8, 9, 10)]
    assert calcular_streak(seguidos, hoje) == (3, 3)
    assert calcular_streak(seguidos + [_utc(2026, 11, 10, 18)], hoje) == (3, 3)  # 2 respostas no mesmo dia contam 1
    # ontem ainda vale (o aluno pode estudar hoje)
    assert calcular_streak([_utc(2026, 11, 9)], hoje) == (1, 1)
    # parou anteontem: sequência atual zera, melhor fica
    antigos = [_utc(2026, 11, d) for d in (1, 2, 3, 4, 8)]
    assert calcular_streak(antigos, hoje) == (0, 4)


def test_dia_no_fuso_de_brasilia():
    # 01:30 UTC do dia 10 = 22:30 do dia 9 em Brasília
    assert dia_local(datetime(2026, 11, 10, 1, 30, tzinfo=timezone.utc)) == date(2026, 11, 9)
    assert dia_local(datetime(2026, 11, 10, 1, 30)) == date(2026, 11, 9)   # sem fuso = UTC


def test_nome_curto():
    assert nome_curto("Ana Souza Lima") == "Ana L."
    assert nome_curto("Bruno") == "Bruno"


def test_ranking(cliente):
    hp = registrar(cliente, "Prof", "prof@ex.com", "professor")
    ha = registrar(cliente, "Ana Souza", "ana@ex.com", "aluno")
    hb = registrar(cliente, "Bruno Lima", "bruno@ex.com", "aluno")
    hc = registrar(cliente, "Carla Dias", "carla@ex.com", "aluno")
    sala = cliente.post("/salas", json={"nome": "9A"}, headers=hp).json()
    for h in (ha, hb, hc):
        cliente.post("/salas/entrar", json={"codigo": sala["codigo"]}, headers=h)
    mod = cliente.post(f"/salas/{sala['id']}/modulos", json={"titulo": "Módulo 1"}, headers=hp).json()
    exs = [cliente.post(f"/modulos/{mod['id']}/exercicios", json={"enunciado": f"questão {i}", "alternativas": ["a", "b"],
                                                                 "indice_correta": 0, "pontos": 10}, headers=hp).json()
           for i in range(2)]
    for ex in exs:
        cliente.post(f"/exercicios/{ex['id']}/responder", json={"alternativa": 0}, headers=hb)   # Bruno: 20
    cliente.post(f"/exercicios/{exs[0]['id']}/responder", json={"alternativa": 0}, headers=ha)  # Ana: 10

    visto_pela_ana = cliente.get(f"/salas/{sala['id']}/ranking", headers=ha).json()
    assert [(r["posicao"], r["nome"], r["pontos"]) for r in visto_pela_ana] == \
        [(1, "Bruno L.", 20), (2, "Ana S.", 10), (3, "Carla D.", 0)]
    assert [r["sou_eu"] for r in visto_pela_ana] == [False, True, False]
    assert all(r["aluno_id"] is None for r in visto_pela_ana)

    visto_pelo_prof = cliente.get(f"/salas/{sala['id']}/ranking", headers=hp).json()
    assert visto_pelo_prof[0]["nome"] == "Bruno Lima" and visto_pelo_prof[0]["aluno_id"] is not None

    fora = registrar(cliente, "Davi", "davi@ex.com", "aluno")
    assert cliente.get(f"/salas/{sala['id']}/ranking", headers=fora).status_code == 404
