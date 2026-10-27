"""Testes da etapa 2 (árvore). Rodar com:  pytest testes/"""

import numpy as np

from ils_adaptativo.arvore import QuestionarioArvore
from ils_adaptativo.calibracao import calibrar
from ils_adaptativo.constantes import N_ITENS, itens_da_dimensao
from ils_adaptativo.escore import escores, intensidades, polos
from ils_adaptativo.gerador import gerar_respondentes
from ils_adaptativo.metricas import avaliar


def _dados(n=4000, seed=0):
    rng = [np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(3)]
    par = calibrar(np.full(N_ITENS, 0.4), np.full(N_ITENS, 0.5), "item_resto", rng[0],
                   n_amostra=3000, max_iteracoes=8)
    df = gerar_respondentes(n, par.a, par.b, np.eye(4), rng[1], rng[2])
    X = df[[f"q{i:02d}" for i in range(1, 45)]].to_numpy()
    e = escores(X)
    return X, polos(e), intensidades(e)


def test_numero_de_questoes_nao_passa_da_profundidade():
    X, p, i = _dados()
    m = QuestionarioArvore([3, 3, 3, 3], min_amostras_folha=5).treinar(X, p, i)
    prev = m.prever(X)
    assert prev["n_questoes"].max() <= 3
    assert (prev["perguntados"].sum(axis=1) == prev["n_total"]).all()


def test_variante_dimensao_so_pergunta_itens_da_propria_dimensao():
    X, p, i = _dados()
    m = QuestionarioArvore([4] * 4, "dimensao", min_amostras_folha=5).treinar(X, p, i)
    for d in range(4):
        permitidos = {c - 1 for c in itens_da_dimensao(d)}
        usados = {m.colunas[d][f] for f in m.arvores[d].tree_.feature if f >= 0}
        assert usados <= permitidos


def test_arvore_completa_reproduz_o_ils():
    # Com todos os 11 itens disponíveis e folhas pequenas, a árvore deve acertar ~100%
    X, p, i = _dados()
    m = QuestionarioArvore([11] * 4, min_amostras_folha=1).treinar(X, p, i)
    assert (m.prever(X)["polo"] == p).mean() > 0.99


def test_proxima_questao_concorda_com_prever():
    # Percorrer a árvore pergunta a pergunta (como a plataforma fará) dá o mesmo polo que prever()
    X, p, i = _dados()
    m = QuestionarioArvore([5] * 4, min_amostras_folha=5).treinar(X, p, i)
    prev = m.prever(X[:200])
    for aluno in range(200):
        for d in range(4):
            respondidas, n = {}, 0
            while True:
                item, polo = m.proxima_questao(d, respondidas)
                if item is None:
                    break
                respondidas[item] = int(X[aluno, item - 1])
                n += 1
            assert polo == prev["polo"][aluno, d]
            assert n == prev["n_questoes"][aluno, d]


def test_metricas_com_acerto_total():
    p = np.array([[1, 0, 1, 0], [0, 1, 0, 1]] * 10)
    r = avaliar(p, p, np.ones_like(p) * 3)
    assert r["geral"]["acuracia_polo_minima"] == 1.0
    assert r["geral"]["media_questoes_total"] == 12


def test_parada_garantida_acerta_tudo_entre_6_e_11_questoes():
    from ils_adaptativo import parada_garantida
    X, p, i = _dados()
    r = parada_garantida.simular(X, parada_garantida.ordem_por_correlacao(X))
    assert (r["polo"] == p).all()
    assert r["n_questoes"].min() >= 6 and r["n_questoes"].max() <= 11
