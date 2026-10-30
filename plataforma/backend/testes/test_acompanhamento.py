"""Testes do painel de desempenho (professor) e do "continuar de onde parou" (aluno)."""

from testes.conftest import registrar


def _ex(certa=1):
    return {"enunciado": "Quanto é 2 + 3?", "alternativas": ["4", "5", "6"], "indice_correta": certa, "pontos": 10}


def _cenario(c):
    hp = registrar(c, "Prof", "prof@ex.com", "professor")
    ha = registrar(c, "Ana Souza", "ana@ex.com", "aluno")
    hb = registrar(c, "Bruno Lima", "bruno@ex.com", "aluno")
    sala = c.post("/salas", json={"nome": "9A"}, headers=hp).json()
    for h in (ha, hb):
        c.post("/salas/entrar", json={"codigo": sala["codigo"]}, headers=h)
    m1 = c.post(f"/salas/{sala['id']}/modulos", json={"titulo": "Frações", "ordem": 1}, headers=hp).json()
    m2 = c.post(f"/salas/{sala['id']}/modulos", json={"titulo": "Potências", "ordem": 2}, headers=hp).json()
    e1 = c.post(f"/modulos/{m1['id']}/exercicios", json=_ex(), headers=hp).json()
    e2 = c.post(f"/modulos/{m1['id']}/exercicios", json=_ex(), headers=hp).json()
    e3 = c.post(f"/modulos/{m2['id']}/exercicios", json=_ex(), headers=hp).json()
    return hp, ha, hb, sala, m1, m2, e1, e2, e3


def _responder(c, h, ex, alt):
    return c.post(f"/exercicios/{ex['id']}/responder", json={"alternativa": alt}, headers=h)


def test_desempenho_da_turma(cliente):
    hp, ha, hb, sala, m1, m2, e1, e2, e3 = _cenario(cliente)
    _responder(cliente, ha, e1, 1)                     # Ana acerta de primeira
    _responder(cliente, hb, e1, 2)                     # Bruno erra (marca C)...
    _responder(cliente, hb, e1, 1)                     # ...e acerta depois
    _responder(cliente, ha, e2, 0)                     # Ana erra e2 (marca A)

    d = cliente.get(f"/salas/{sala['id']}/desempenho", headers=hp).json()
    assert d["n_alunos"] == 2 and d["total_exercicios"] == 3
    ex1, ex2 = d["modulos"][0]["exercicios"]
    assert ex1["responderam"] == 2 and ex1["acerto_primeira"] == 0.5        # vale a 1ª resposta
    assert ex1["erro_comum"] == {"alternativa": 2, "quantos": 1}
    assert ex2["acerto_primeira"] == 0.0 and ex2["erro_comum"]["alternativa"] == 0
    assert d["modulos"][1]["exercicios"][0]["acerto_primeira"] is None      # ninguém respondeu
    assert d["modulos"][0]["concluiram"] == 0                                # ninguém acertou e1 E e2
    assert d["acerto_primeira_medio"] == round(1 / 3, 4)
    ana = next(a for a in d["alunos"] if a["nome"] == "Ana Souza")
    assert ana["acertados"] == 1 and ana["pontos"] == 10 and ana["ultima_atividade"]


def test_desempenho_so_para_o_professor_dono(cliente):
    hp, ha, *_ = _cenario(cliente)
    sala_id = cliente.get("/salas", headers=hp).json()[0]["id"]
    assert cliente.get(f"/salas/{sala_id}/desempenho", headers=ha).status_code == 403
    outro = registrar(cliente, "Outro", "outro@ex.com", "professor")
    assert cliente.get(f"/salas/{sala_id}/desempenho", headers=outro).status_code == 404


def test_continuar_de_onde_parou(cliente):
    hp, ha, hb, sala, m1, m2, e1, e2, e3 = _cenario(cliente)
    # sem nada feito: o primeiro módulo
    r = cliente.get("/eu/continuar", headers=ha).json()
    assert r["modulo_id"] == m1["id"] and r["feitos"] == 0 and r["total"] == 2
    # respondeu no módulo 2: continua nele
    _responder(cliente, ha, e3, 0)
    assert cliente.get("/eu/continuar", headers=ha).json()["modulo_id"] == m2["id"]
    # terminou o módulo 2: volta para o que falta (módulo 1)
    _responder(cliente, ha, e3, 1)
    r = cliente.get("/eu/continuar", headers=ha).json()
    assert r["modulo_id"] == m1["id"] and r["sala_nome"] == "9A"
    # fez tudo: em dia
    _responder(cliente, ha, e1, 1)
    _responder(cliente, ha, e2, 1)
    assert cliente.get("/eu/continuar", headers=ha).json() is None
    # professor não usa esta rota
    assert cliente.get("/eu/continuar", headers=hp).status_code == 403
