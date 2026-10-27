"""Testes da etapa 4a — parte em numpy (máscaras, codificação, referência de TRI)."""

import numpy as np

from ils_adaptativo.avaliacao_parcial import ece, prob_tac
from ils_adaptativo.calibracao import calibrar
from ils_adaptativo.constantes import COLUNAS_ITENS, N_ITENS, itens_da_dimensao
from ils_adaptativo.gerador import gerar_respondentes
from ils_adaptativo.mascaras import codificar, mascara_k_itens, sortear_mascaras
from ils_adaptativo.tac import TAC


def _dados(n=500):
    rng = [np.random.default_rng(s) for s in np.random.SeedSequence(0).spawn(3)]
    par = calibrar(np.full(N_ITENS, 0.4), np.full(N_ITENS, 0.5), "item_resto", rng[0],
                   n_amostra=3000, max_iteracoes=8)
    X = gerar_respondentes(n, par.a, par.b, np.eye(4), rng[1], rng[2])[COLUNAS_ITENS].to_numpy()
    tac = TAC()
    tac.a, tac.b = par.a.copy(), par.b.copy()
    return X, tac


def test_mascaras_cobrem_de_0_a_11_itens_por_dimensao():
    m = sortear_mascaras(24000, np.random.default_rng(0))
    for d in range(4):
        contagem = np.bincount(m[:, [i - 1 for i in itens_da_dimensao(d)]].sum(axis=1), minlength=12)
        assert len(contagem) == 12 and contagem.min() > 1500  # ~2000 em cada valor


def test_codificacao():
    X = np.array([[1, 0] * 22])
    m = np.zeros((1, 44), dtype=bool)
    m[0, :2] = True
    e = codificar(X, m)
    assert e.shape == (1, 88)
    assert e[0, :2].tolist() == [1, 1] and e[0, 2:44].sum() == 0
    assert e[0, 44:46].tolist() == [1, -1] and e[0, 46:].sum() == 0


def test_mascara_k_itens():
    m = mascara_k_itens(10, 1, 3, np.random.default_rng(0), "todas")
    assert (m[:, [i - 1 for i in itens_da_dimensao(1)]].sum(axis=1) == 3).all()
    assert (m.sum(axis=1) == 33 + 3).all()


def test_tri_com_mascara_igual_a_trajetoria_do_tac():
    X, tac = _dados()
    for d in range(4):
        traj = tac.trajetoria(X, d)
        for k in (0, 3, 7, 11):
            m = np.zeros_like(X, dtype=bool)
            for aluno in range(len(X)):
                m[aluno, traj["ordem"][aluno, :k] - 1] = True
            assert np.allclose(tac.prob_polo_mascara(X, m, d), traj["p_escore"][k])


def test_tri_com_mascara_e_calibrada():
    # a probabilidade da TRI com os parâmetros verdadeiros deve ser bem calibrada
    X, tac = _dados(n=3000)
    from ils_adaptativo.escore import escores, polos
    p = prob_tac(tac)(X, sortear_mascaras(len(X), np.random.default_rng(1)))
    assert ece(p[:, 0], polos(escores(X))[:, 0]) < 0.03
