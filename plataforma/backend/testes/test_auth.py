"""Testes de cadastro, login e direitos do titular (LGPD)."""

from testes.conftest import registrar


def _corpo(**extra):
    base = {"nome": "Ana", "email": "ana@ex.com", "senha": "senha-forte-123", "perfil": "aluno",
            "aceite_termos": True}
    return {**base, **extra}


def test_registro_login_e_eu(cliente):
    h = registrar(cliente, "Ana", "Ana@Ex.com", "aluno")
    r = cliente.get("/auth/eu", headers=h)
    assert r.status_code == 200
    assert r.json()["email"] == "ana@ex.com"          # e-mail normalizado em minúsculas
    assert "senha" not in r.text and "senha_hash" not in r.text


def test_validacoes_do_cadastro(cliente):
    assert cliente.post("/auth/registrar", json=_corpo(aceite_termos=False)).status_code == 422
    assert cliente.post("/auth/registrar", json=_corpo(senha="curta")).status_code == 422
    assert cliente.post("/auth/registrar", json=_corpo(email="sem-arroba")).status_code == 422
    assert cliente.post("/auth/registrar", json=_corpo(perfil="admin")).status_code == 422
    assert cliente.post("/auth/registrar", json=_corpo()).status_code == 201
    assert cliente.post("/auth/registrar", json=_corpo()).status_code == 409   # e-mail repetido


def test_login_errado_nao_revela_se_email_existe(cliente):
    registrar(cliente, "Ana", "ana@ex.com", "aluno")
    a = cliente.post("/auth/login", json={"email": "ana@ex.com", "senha": "errada-123"})
    b = cliente.post("/auth/login", json={"email": "ninguem@ex.com", "senha": "errada-123"})
    assert a.status_code == b.status_code == 401 and a.json() == b.json()


def test_rotas_protegidas_exigem_token_valido(cliente):
    assert cliente.get("/auth/eu").status_code == 401
    assert cliente.get("/auth/eu", headers={"Authorization": "Bearer abc.def.ghi"}).status_code == 401
    h = registrar(cliente, "Ana", "ana@ex.com", "aluno")
    token = h["Authorization"].split()[1]
    adulterado = token[:-3] + ("aaa" if not token.endswith("aaa") else "bbb")
    assert cliente.get("/auth/eu", headers={"Authorization": f"Bearer {adulterado}"}).status_code == 401


def test_senha_guardada_com_hash():
    from app.seguranca import conferir_senha, gerar_hash
    h = gerar_hash("minha-senha", iteracoes=1000)
    assert "minha-senha" not in h and h.startswith("pbkdf2_sha256$1000$")
    assert conferir_senha("minha-senha", h) and not conferir_senha("outra", h)
    assert gerar_hash("minha-senha", iteracoes=1000) != h        # sal diferente a cada vez


def test_exportar_e_excluir_conta(cliente):
    hp = registrar(cliente, "Prof", "prof@ex.com", "professor")
    ha = registrar(cliente, "Ana", "ana@ex.com", "aluno")
    codigo = cliente.post("/salas", json={"nome": "9A"}, headers=hp).json()["codigo"]
    cliente.post("/salas/entrar", json={"codigo": codigo}, headers=ha)

    sala_id = cliente.get("/salas", headers=hp).json()[0]["id"]
    mod = cliente.post(f"/salas/{sala_id}/modulos", json={"titulo": "Módulo 1"}, headers=hp).json()
    ex = cliente.post(f"/modulos/{mod['id']}/exercicios", json={"enunciado": "Quanto é 1 + 1?", "alternativas": ["a", "b"],
                                                               "indice_correta": 0}, headers=hp).json()
    cliente.post(f"/exercicios/{ex['id']}/responder", json={"alternativa": 0}, headers=ha)

    dados = cliente.get("/auth/eu/dados", headers=ha).json()
    assert dados["conta"]["email"] == "ana@ex.com" and dados["salas"][0]["sala"] == "9A"
    assert "consentimento_em" in dados and dados["respostas"][0]["correta"] is True

    assert cliente.delete("/auth/eu", headers=ha).status_code == 204
    assert cliente.get("/auth/eu", headers=ha).status_code == 401           # token de conta apagada
    sala = cliente.get("/salas", headers=hp).json()[0]
    assert sala["n_alunos"] == 0                                           # matrícula foi junto

    assert cliente.delete("/auth/eu", headers=hp).status_code == 204       # professor: salas vão junto
    hp2 = registrar(cliente, "Prof2", "prof2@ex.com", "professor")
    assert cliente.get("/salas", headers=hp2).json() == []
