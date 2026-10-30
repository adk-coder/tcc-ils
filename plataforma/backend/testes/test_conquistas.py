"""Adesivos de conquista: regras (função pura) e rota."""

from datetime import datetime, timedelta, timezone

from app.conquistas import RespostaSimples as R
from app.conquistas import calcular_conquistas
from testes.conftest import registrar

T0 = datetime(2026, 11, 10, 15, tzinfo=timezone.utc)


def _por_id(lista):
    return {a["id"]: a for a in lista}


def test_nada_feito():
    a = _por_id(calcular_conquistas([], {}, None))
    assert not any(x["ganho"] for x in a.values())
    assert a["dez_na_conta"]["progresso"] == 0 and a["dez_na_conta"]["meta"] == 10


def test_acertos_de_primeira_e_persistencia():
    resp = [R(1, True, 10, T0), R(2, False, 0, T0 + timedelta(minutes=1)), R(2, True, 0, T0 + timedelta(minutes=2))]
    a = _por_id(calcular_conquistas(resp, {7: {1, 2}}, None))
    assert a["primeiro_acerto"]["ganho"] and a["primeiro_acerto"]["ganho_em"] == T0
    assert a["na_primeira"]["progresso"] == 1 and not a["na_primeira"]["ganho"]   # o 2 foi acertado depois de errar
    assert a["nao_desisto"]["ganho"]
    assert a["modulo_fechado"]["ganho"]                                            # acertou 1 e 2 = módulo 7
    assert not a["dez_na_conta"]["ganho"] and a["dez_na_conta"]["progresso"] == 2


def test_modulo_vazio_nao_conta():
    a = _por_id(calcular_conquistas([R(1, True, 10, T0)], {5: set(), 6: {1, 2}}, None))
    assert not a["modulo_fechado"]["ganho"]


def test_dias_seguidos():
    dias = [T0 + timedelta(days=d) for d in (0, 1, 2, 4)]                          # 3 seguidos, depois quebra
    a = _por_id(calcular_conquistas([R(i, True, 10, t) for i, t in enumerate(dias)], {}, None))
    assert a["tres_dias"]["ganho"] and a["tres_dias"]["ganho_em"].day == 12
    assert not a["semana_firme"]["ganho"] and a["semana_firme"]["progresso"] == 3


def test_estilo():
    a = _por_id(calcular_conquistas([], {}, T0))
    assert a["me_conheco"]["ganho"]


def test_rota_conquistas(cliente):
    hp = registrar(cliente, "Prof", "prof@ex.com", "professor")
    ha = registrar(cliente, "Ana Souza", "ana@ex.com", "aluno")
    sala = cliente.post("/salas", json={"nome": "9A"}, headers=hp).json()
    cliente.post("/salas/entrar", json={"codigo": sala["codigo"]}, headers=ha)
    mod = cliente.post(f"/salas/{sala['id']}/modulos", json={"titulo": "Frações"}, headers=hp).json()
    ex = cliente.post(f"/modulos/{mod['id']}/exercicios", headers=hp,
                      json={"enunciado": "2 + 3?", "alternativas": ["4", "5"], "indice_correta": 1}).json()
    cliente.post(f"/exercicios/{ex['id']}/responder", json={"alternativa": 1}, headers=ha)
    a = _por_id(cliente.get("/eu/conquistas", headers=ha).json())
    assert len(a) == 8
    assert a["primeiro_acerto"]["ganho"] and a["modulo_fechado"]["ganho"]
    assert cliente.get("/eu/conquistas", headers=hp).status_code == 403
