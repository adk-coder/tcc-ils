"""Testes do perfil da turma (P15): perfil agregado e anônimo dos estilos de aprendizagem."""

from datetime import datetime, timezone

from testes.conftest import registrar


# ---------------------------------------------------------------------------
# Auxiliares

def _agora():
    return datetime.now(timezone.utc)


def _resultado_padrao(polo: str):
    """
    Resultado com os quatro polos alinhados na direção 'a' ou 'b'.
      polo="a" → ativo, sensorial, visual, sequencial
      polo="b" → reflexivo, intuitivo, verbal, global
    """
    pares = [
        ("ati_ref", "ativo", "reflexivo"),
        ("sen_int", "sensorial", "intuitivo"),
        ("vis_ver", "visual", "verbal"),
        ("seq_glo", "sequencial", "global"),
    ]
    return [
        {
            "dimensao": dim,
            "polo": a if polo == "a" else b,
            "polo_oposto": b if polo == "a" else a,
            "confianca": 0.9,
            "n_questoes": 6,
        }
        for dim, a, b in pares
    ]


def _completar_questionario(sessao, aluno_id: int, resultado: list):
    from app.modelos import QuestionarioEstilo
    q = QuestionarioEstilo(aluno_id=aluno_id, respostas=[], resultado=resultado, concluido_em=_agora())
    sessao.add(q)
    sessao.commit()


def _id_usuario(c, headers):
    return c.get("/auth/eu", headers=headers).json()["id"]


def _matricular(c, sala, ha):
    c.post("/salas/entrar", json={"codigo": sala["codigo"]}, headers=ha)


def _cenario_base(c, s, n_completos: int, n_polo_b: int = 0):
    """
    Cria um professor, uma sala e `n_completos` alunos com questionário concluído.
    Os primeiros `n_completos - n_polo_b` usam polo "a"; os demais, polo "b".
    Devolve (hp, sala, lista de ids dos alunos com questionário concluído).
    """
    hp = registrar(c, "Prof", "prof@ex.com", "professor")
    sala = c.post("/salas", json={"nome": "9A"}, headers=hp).json()
    aluno_ids = []
    for i in range(n_completos):
        ha = registrar(c, f"Aluno {i}", f"aluno{i}@ex.com", "aluno")
        _matricular(c, sala, ha)
        aid = _id_usuario(c, ha)
        polo = "b" if i >= (n_completos - n_polo_b) else "a"
        _completar_questionario(s, aid, _resultado_padrao(polo))
        aluno_ids.append(aid)
    return hp, sala, aluno_ids


# ---------------------------------------------------------------------------
# Testes de permissão

def test_aluno_recebe_403(cliente):
    hp = registrar(cliente, "Prof", "prof@ex.com", "professor")
    ha = registrar(cliente, "Ana", "ana@ex.com", "aluno")
    sala = cliente.post("/salas", json={"nome": "9A"}, headers=hp).json()
    _matricular(cliente, sala, ha)
    r = cliente.get(f"/salas/{sala['id']}/perfil-turma", headers=ha)
    assert r.status_code == 403


def test_professor_outra_sala_recebe_403(cliente):
    hp1 = registrar(cliente, "Prof 1", "p1@ex.com", "professor")
    hp2 = registrar(cliente, "Prof 2", "p2@ex.com", "professor")
    sala = cliente.post("/salas", json={"nome": "9A"}, headers=hp1).json()
    r = cliente.get(f"/salas/{sala['id']}/perfil-turma", headers=hp2)
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Regra do mínimo de respondentes

def test_zero_respondentes(cliente_e_sessao):
    c, _s = cliente_e_sessao
    hp = registrar(c, "Prof", "prof@ex.com", "professor")
    sala = c.post("/salas", json={"nome": "9A"}, headers=hp).json()
    r = c.get(f"/salas/{sala['id']}/perfil-turma", headers=hp).json()
    assert r["respondentes"] == 0
    assert r["minimo_atingido"] is False
    assert r["dimensoes"] is None


def test_menos_de_5_respondentes(cliente_e_sessao):
    c, s = cliente_e_sessao
    hp, sala, _ = _cenario_base(c, s, n_completos=4)
    r = c.get(f"/salas/{sala['id']}/perfil-turma", headers=hp).json()
    assert r["respondentes"] == 4
    assert r["minimo_atingido"] is False
    assert r["dimensoes"] is None


def test_exatamente_5_respondentes_ja_mostra(cliente_e_sessao):
    c, s = cliente_e_sessao
    hp, sala, _ = _cenario_base(c, s, n_completos=5)
    r = c.get(f"/salas/{sala['id']}/perfil-turma", headers=hp).json()
    assert r["minimo_atingido"] is True
    assert r["dimensoes"] is not None


# ---------------------------------------------------------------------------
# Percentuais

def test_percentuais_corretos(cliente_e_sessao):
    """3 alunos com polo "a" + 2 com polo "b" → 60 % / 40 %."""
    c, s = cliente_e_sessao
    hp, sala, _ = _cenario_base(c, s, n_completos=5, n_polo_b=2)
    r = c.get(f"/salas/{sala['id']}/perfil-turma", headers=hp).json()

    assert r["respondentes"] == 5
    assert r["minimo_atingido"] is True
    assert len(r["dimensoes"]) == 4

    dim_ati = next(d for d in r["dimensoes"] if d["dimensao"] == "ati_ref")
    assert dim_ati["polo_a"] == "ativo" and dim_ati["polo_b"] == "reflexivo"
    assert dim_ati["percentual_a"] == 60.0
    assert dim_ati["percentual_b"] == 40.0

    # Todas as 4 dimensões presentes na ordem correta
    chaves = [d["dimensao"] for d in r["dimensoes"]]
    assert chaves == ["ati_ref", "sen_int", "vis_ver", "seq_glo"]


def test_percentuais_somam_100(cliente_e_sessao):
    c, s = cliente_e_sessao
    hp, sala, _ = _cenario_base(c, s, n_completos=7, n_polo_b=3)  # 4 "a", 3 "b"
    r = c.get(f"/salas/{sala['id']}/perfil-turma", headers=hp).json()
    for d in r["dimensoes"]:
        total = round(d["percentual_a"] + d["percentual_b"], 10)
        assert total == 100.0, f"{d['dimensao']}: {d['percentual_a']} + {d['percentual_b']} ≠ 100"


# ---------------------------------------------------------------------------
# Privacidade: resposta não contém dados individuais

def test_resposta_sem_dados_individuais(cliente_e_sessao):
    c, s = cliente_e_sessao
    hp, sala, aluno_ids = _cenario_base(c, s, n_completos=5)
    r = c.get(f"/salas/{sala['id']}/perfil-turma", headers=hp).json()

    # Campos de topo permitidos
    assert set(r.keys()) == {"respondentes", "minimo_atingido", "dimensoes"}

    # Cada dimensão tem apenas campos agregados
    for d in r["dimensoes"]:
        assert set(d.keys()) == {"dimensao", "polo_a", "polo_b", "percentual_a", "percentual_b"}


def test_so_conta_alunos_matriculados(cliente_e_sessao):
    """Aluno que completou o questionário mas NÃO está na sala não entra na conta."""
    c, s = cliente_e_sessao
    hp = registrar(c, "Prof", "prof@ex.com", "professor")
    sala = c.post("/salas", json={"nome": "9A"}, headers=hp).json()

    # 3 alunos matriculados + questionário
    for i in range(3):
        ha = registrar(c, f"Aluno {i}", f"aluno{i}@ex.com", "aluno")
        _matricular(c, sala, ha)
        _completar_questionario(s, _id_usuario(c, ha), _resultado_padrao("a"))

    # 10 alunos NÃO matriculados com questionário completo
    for i in range(3, 13):
        ha = registrar(c, f"Outro {i}", f"outro{i}@ex.com", "aluno")
        _completar_questionario(s, _id_usuario(c, ha), _resultado_padrao("a"))

    r = c.get(f"/salas/{sala['id']}/perfil-turma", headers=hp).json()
    assert r["respondentes"] == 3          # só os 3 matriculados
    assert r["minimo_atingido"] is False


def test_so_conta_questionarios_concluidos(cliente_e_sessao):
    """Aluno que iniciou mas não concluiu o questionário não conta."""
    from app.modelos import QuestionarioEstilo

    c, s = cliente_e_sessao
    hp = registrar(c, "Prof", "prof@ex.com", "professor")
    sala = c.post("/salas", json={"nome": "9A"}, headers=hp).json()

    # 5 alunos matriculados: 3 concluíram, 2 apenas iniciaram (sem concluido_em)
    for i in range(3):
        ha = registrar(c, f"Aluno {i}", f"aluno{i}@ex.com", "aluno")
        _matricular(c, sala, ha)
        _completar_questionario(s, _id_usuario(c, ha), _resultado_padrao("a"))

    for i in range(3, 5):
        ha = registrar(c, f"Aluno {i}", f"aluno{i}@ex.com", "aluno")
        _matricular(c, sala, ha)
        aid = _id_usuario(c, ha)
        q = QuestionarioEstilo(aluno_id=aid, respostas=[[1, 1], [2, 0]])  # iniciado, não concluído
        s.add(q)
        s.commit()

    r = c.get(f"/salas/{sala['id']}/perfil-turma", headers=hp).json()
    assert r["respondentes"] == 3          # só os 3 que concluíram
    assert r["minimo_atingido"] is False
