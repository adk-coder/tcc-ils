"""Testes do questionário adaptativo de estilos de aprendizagem (motor + rotas)."""

import pytest

from app.ils.motor import MotorILS, dimensao_do_item
from app.main import app
from app.rotas.estilo import obter_motor
from testes.conftest import registrar


def _motor(limiar=0.9):
    # modelo de brinquedo: todos os itens iguais (a = 1,5; b = 0). O real vem de ia/.
    return MotorILS([1.5] * 44, [0.0] * 44, [limiar] * 4)


@pytest.fixture
def com_motor(cliente):
    app.dependency_overrides[obter_motor] = _motor
    yield cliente


# ------------------------------------------------------------------ motor
def test_respostas_iguais_decidem_e_param():
    m = _motor(limiar=0.999)
    resp = []
    while (item := m.proxima(resp)["item"]) is not None:
        resp.append((item, 1))                             # sempre "a"
    final = m.proxima(resp)["dimensoes"]
    assert all(d["polo"] == 1 for d in final)
    # nunca passa de 6 por dimensão: com 6 respostas "a" o polo já está decidido
    assert all(d["n_questoes"] <= 6 for d in final)


def test_nunca_repete_item_nem_passa_de_11_por_dimensao():
    m = _motor(limiar=0.99)
    resp = []
    while (item := m.proxima(resp)["item"]) is not None:
        resp.append((item, len(resp) % 2))                 # alterna a / b: o caso mais indeciso
    itens = [i for i, _ in resp]
    assert len(itens) == len(set(itens)) <= 44
    for d in range(4):
        assert sum(dimensao_do_item(i) == d for i in itens) <= 11


def test_rodizio_entre_as_dimensoes():
    m = _motor()
    resp = []
    for _ in range(4):
        item = m.proxima(resp)["item"]
        resp.append((item, 1))
    # as 4 primeiras perguntas são uma de cada dimensão
    assert sorted(dimensao_do_item(i) for i, _ in resp) == [0, 1, 2, 3]


# ------------------------------------------------------------------ rotas
def test_fluxo_completo(com_motor):
    ha = registrar(com_motor, "Ana Souza", "ana@ex.com", "aluno")
    assert com_motor.get("/eu/estilo", headers=ha).json()["status"] == "nao_iniciado"

    estado = com_motor.post("/eu/estilo/iniciar", headers=ha).json()
    assert estado["status"] == "em_andamento" and estado["pergunta"]["numero"] == 1
    assert isinstance(estado["textos_provisorios"], bool)
    n = 0
    while estado["status"] == "em_andamento":
        estado = com_motor.post("/eu/estilo/responder", headers=ha,
                                json={"item": estado["pergunta"]["item"], "resposta": "a"}).json()
        n += 1
    assert estado["status"] == "concluido" and estado["respondidas"] == n < 44
    assert [d["polo"] for d in estado["resultado"]] == ["ativo", "sensorial", "visual", "sequencial"]
    assert all(0.5 <= d["confianca"] <= 1 for d in estado["resultado"])

    # continua concluído ao recarregar; responder de novo não é aceito
    assert com_motor.get("/eu/estilo", headers=ha).json()["status"] == "concluido"
    assert com_motor.post("/eu/estilo/responder", headers=ha, json={"item": 1, "resposta": "a"}).status_code == 409
    # refazer começa do zero
    assert com_motor.post("/eu/estilo/iniciar", headers=ha).json()["respondidas"] == 0


def test_so_aceita_a_pergunta_atual(com_motor):
    ha = registrar(com_motor, "Ana Souza", "ana@ex.com", "aluno")
    estado = com_motor.post("/eu/estilo/iniciar", headers=ha).json()
    atual = estado["pergunta"]["item"]
    outro = 44 if atual != 44 else 43
    assert com_motor.post("/eu/estilo/responder", headers=ha,
                          json={"item": outro, "resposta": "a"}).status_code == 409
    # clique duplo: a 2ª resposta à mesma pergunta é recusada
    assert com_motor.post("/eu/estilo/responder", headers=ha, json={"item": atual, "resposta": "b"}).status_code == 200
    assert com_motor.post("/eu/estilo/responder", headers=ha, json={"item": atual, "resposta": "b"}).status_code == 409


def test_professor_nao_faz_e_lgpd(com_motor):
    hp = registrar(com_motor, "Prof", "prof@ex.com", "professor")
    assert com_motor.get("/eu/estilo", headers=hp).status_code == 403

    ha = registrar(com_motor, "Ana Souza", "ana@ex.com", "aluno")
    estado = com_motor.post("/eu/estilo/iniciar", headers=ha).json()
    com_motor.post("/eu/estilo/responder", headers=ha, json={"item": estado["pergunta"]["item"], "resposta": "a"})
    dados = com_motor.get("/auth/eu/dados", headers=ha).json()
    assert dados["estilo_de_aprendizagem"]["respostas"] == [{"item": estado["pergunta"]["item"], "resposta": "a"}]
    assert com_motor.delete("/auth/eu", headers=ha).status_code == 204


def test_sem_modelo_exportado_responde_503(cliente, monkeypatch, tmp_path):
    from app.rotas import estilo
    estilo._motor_do_arquivo.cache_clear()
    monkeypatch.setattr("app.ils.motor.CAMINHO_MODELO", tmp_path / "nao_existe.json")
    ha = registrar(cliente, "Ana Souza", "ana@ex.com", "aluno")
    assert cliente.get("/eu/estilo", headers=ha).status_code == 503
    estilo._motor_do_arquivo.cache_clear()
