"""Testes de módulos, exercícios e respostas."""

from testes.conftest import registrar

EX = {"enunciado": "Quanto é 2 + 3?", "alternativas": ["4", "5", "6"], "indice_correta": 1,
      "explicacao": "2 + 3 = 5", "pontos": 10}


def _cenario(cliente):
    hp = registrar(cliente, "Prof", "prof@ex.com", "professor")
    ha = registrar(cliente, "Ana Souza", "ana@ex.com", "aluno")
    sala = cliente.post("/salas", json={"nome": "9A"}, headers=hp).json()
    cliente.post("/salas/entrar", json={"codigo": sala["codigo"]}, headers=ha)
    mod = cliente.post(f"/salas/{sala['id']}/modulos", json={"titulo": "Frações", "conteudo": "texto"},
                       headers=hp).json()
    ex = cliente.post(f"/modulos/{mod['id']}/exercicios", json=EX, headers=hp).json()
    return hp, ha, sala, mod, ex


def test_professor_cria_modulo_e_exercicio(cliente):
    hp, _, sala, mod, ex = _cenario(cliente)
    assert ex["indice_correta"] == 1
    lista = cliente.get(f"/salas/{sala['id']}/modulos", headers=hp).json()
    assert lista[0]["titulo"] == "Frações" and lista[0]["n_exercicios"] == 1


def test_validacao_do_exercicio(cliente):
    hp, _, _, mod, _ = _cenario(cliente)
    url = f"/modulos/{mod['id']}/exercicios"
    assert cliente.post(url, json={**EX, "indice_correta": 3}, headers=hp).status_code == 422
    assert cliente.post(url, json={**EX, "alternativas": ["só uma"]}, headers=hp).status_code == 422
    assert cliente.post(url, json={**EX, "alternativas": ["a", " "]}, headers=hp).status_code == 422


def test_aluno_nao_ve_resposta_antes_de_responder(cliente):
    _, ha, _, mod, _ = _cenario(cliente)
    r = cliente.get(f"/modulos/{mod['id']}", headers=ha)
    assert r.status_code == 200
    ex = r.json()["exercicios"][0]
    assert "indice_correta" not in ex and "explicacao" not in ex
    assert ex["ja_respondeu"] is False and r.json()["conteudo"] == "texto"


def test_pontos_so_na_primeira_tentativa_certa(cliente):
    _, ha, sala, mod, ex = _cenario(cliente)
    url = f"/exercicios/{ex['id']}/responder"
    errada = cliente.post(url, json={"alternativa": 0}, headers=ha).json()
    assert errada == {"correta": False, "indice_correta": 1, "explicacao": "2 + 3 = 5",
                      "pontos_ganhos": 0, "primeira_tentativa": True}
    certa = cliente.post(url, json={"alternativa": 1}, headers=ha).json()
    assert certa["correta"] and certa["pontos_ganhos"] == 0          # já viu a resposta: sem pontos
    assert cliente.get("/eu/progresso", headers=ha).json()["pontos"] == 0
    resumo = cliente.get(f"/salas/{sala['id']}/modulos", headers=ha).json()[0]
    assert resumo["n_acertados"] == 1
    assert cliente.post(url, json={"alternativa": 9}, headers=ha).status_code == 422


def test_acerto_de_primeira_pontua(cliente):
    _, ha, _, _, ex = _cenario(cliente)
    r = cliente.post(f"/exercicios/{ex['id']}/responder", json={"alternativa": 1}, headers=ha).json()
    assert r["pontos_ganhos"] == 10
    p = cliente.get("/eu/progresso", headers=ha).json()
    assert p["pontos"] == 10 and p["exercicios_acertados"] == 1 and p["streak_atual"] == 1


def test_permissoes(cliente):
    hp, ha, sala, mod, ex = _cenario(cliente)
    # aluno não cria nem edita conteúdo
    assert cliente.post(f"/salas/{sala['id']}/modulos", json={"titulo": "X"}, headers=ha).status_code == 403
    assert cliente.put(f"/exercicios/{ex['id']}", json=EX, headers=ha).status_code == 403
    # professor não responde exercício
    assert cliente.post(f"/exercicios/{ex['id']}/responder", json={"alternativa": 1}, headers=hp).status_code == 403
    # quem é de fora da sala não vê nada (404)
    outro_prof = registrar(cliente, "Outro", "outro@ex.com", "professor")
    fora = registrar(cliente, "Carla", "carla@ex.com", "aluno")
    for h in (outro_prof, fora):
        assert cliente.get(f"/modulos/{mod['id']}", headers=h).status_code == 404
        assert cliente.get(f"/salas/{sala['id']}/modulos", headers=h).status_code == 404
    assert cliente.put(f"/modulos/{mod['id']}", json={"titulo": "Hack"}, headers=outro_prof).status_code == 404
    assert cliente.post(f"/exercicios/{ex['id']}/responder", json={"alternativa": 1}, headers=fora).status_code == 404


def test_editar_e_apagar(cliente):
    hp, ha, sala, mod, ex = _cenario(cliente)
    cliente.post(f"/exercicios/{ex['id']}/responder", json={"alternativa": 1}, headers=ha)
    novo = {**EX, "enunciado": "Quanto é 3 + 3?", "alternativas": ["6", "7"], "indice_correta": 0}
    assert cliente.put(f"/exercicios/{ex['id']}", json=novo, headers=hp).json()["enunciado"] == "Quanto é 3 + 3?"
    assert cliente.put(f"/modulos/{mod['id']}", json={"titulo": "Frações I"}, headers=hp).json()["titulo"] == "Frações I"
    assert cliente.delete(f"/modulos/{mod['id']}", headers=hp).status_code == 204       # leva exercícios e respostas
    assert cliente.get(f"/salas/{sala['id']}/modulos", headers=hp).json() == []
    assert cliente.get("/eu/progresso", headers=ha).json()["pontos"] == 0
