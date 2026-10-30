"""Testes das salas virtuais e das regras de acesso."""

from testes.conftest import registrar


def _cenario(cliente):
    hp = registrar(cliente, "Prof", "prof@ex.com", "professor")
    ha = registrar(cliente, "Ana", "ana@ex.com", "aluno")
    hb = registrar(cliente, "Bruno", "bruno@ex.com", "aluno")
    sala = cliente.post("/salas", json={"nome": "9º ano A"}, headers=hp).json()
    return hp, ha, hb, sala


def test_professor_cria_sala_com_codigo(cliente):
    hp, _, _, sala = _cenario(cliente)
    assert len(sala["codigo"]) == 6 and sala["nome"] == "9º ano A" and sala["n_alunos"] == 0


def test_aluno_nao_cria_sala(cliente):
    _, ha, _, _ = _cenario(cliente)
    assert cliente.post("/salas", json={"nome": "X"}, headers=ha).status_code == 403


def test_aluno_entra_pelo_codigo_e_nao_ve_codigo(cliente):
    hp, ha, _, sala = _cenario(cliente)
    r = cliente.post("/salas/entrar", json={"codigo": sala["codigo"].lower()}, headers=ha)
    assert r.status_code == 200 and r.json()["codigo"] == ""
    cliente.post("/salas/entrar", json={"codigo": sala["codigo"]}, headers=ha)     # entrar 2x não duplica
    assert cliente.get("/salas", headers=hp).json()[0]["n_alunos"] == 1
    assert [s["nome"] for s in cliente.get("/salas", headers=ha).json()] == ["9º ano A"]
    assert cliente.post("/salas/entrar", json={"codigo": "ZZZZZZ"}, headers=ha).status_code == 404


def test_visibilidade_da_sala(cliente):
    hp, ha, hb, sala = _cenario(cliente)
    cliente.post("/salas/entrar", json={"codigo": sala["codigo"]}, headers=ha)
    cliente.post("/salas/entrar", json={"codigo": sala["codigo"]}, headers=hb)

    prof = cliente.get(f"/salas/{sala['id']}", headers=hp).json()
    assert [a["nome"] for a in prof["alunos"]] == ["Ana", "Bruno"] and prof["codigo"]

    aluno = cliente.get(f"/salas/{sala['id']}", headers=ha).json()
    assert aluno["alunos"] == [] and aluno["codigo"] == "" and aluno["professor_nome"] == "Prof"

    outro_prof = registrar(cliente, "Outro", "outro@ex.com", "professor")
    assert cliente.get(f"/salas/{sala['id']}", headers=outro_prof).status_code == 404
    fora = registrar(cliente, "Carla", "carla@ex.com", "aluno")
    assert cliente.get(f"/salas/{sala['id']}", headers=fora).status_code == 404


def test_remover_aluno_e_sair(cliente):
    hp, ha, hb, sala = _cenario(cliente)
    cliente.post("/salas/entrar", json={"codigo": sala["codigo"]}, headers=ha)
    cliente.post("/salas/entrar", json={"codigo": sala["codigo"]}, headers=hb)
    ana_id = cliente.get("/auth/eu", headers=ha).json()["id"]

    assert cliente.delete(f"/salas/{sala['id']}/alunos/{ana_id}", headers=hb).status_code == 403
    assert cliente.delete(f"/salas/{sala['id']}/alunos/{ana_id}", headers=hp).status_code == 204
    assert cliente.get(f"/salas/{sala['id']}", headers=ha).status_code == 404     # perdeu o acesso

    assert cliente.delete(f"/salas/{sala['id']}/sair", headers=hb).status_code == 204
    assert cliente.get("/salas", headers=hp).json()[0]["n_alunos"] == 0
