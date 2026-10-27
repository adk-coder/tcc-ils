"""Testes da etapa 4a — classificador MLP (precisa de PyTorch)."""

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from ils_adaptativo import classificador as clf  # noqa: E402
from ils_adaptativo.calibracao import calibrar  # noqa: E402
from ils_adaptativo.constantes import COLUNAS_ITENS, N_ITENS  # noqa: E402
from ils_adaptativo.escore import escores, polos  # noqa: E402
from ils_adaptativo.gerador import gerar_respondentes  # noqa: E402

CFG = {"camadas": [64, 64], "dropout": 0.0, "lr": 0.003, "weight_decay": 0.0,
       "lote": 256, "max_epocas": 15, "paciencia": 15}


def _dados(n, seed):
    rng = [np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(3)]
    par = calibrar(np.full(N_ITENS, 0.4), np.full(N_ITENS, 0.5), "item_resto", rng[0],
                   n_amostra=3000, max_iteracoes=8)
    X = gerar_respondentes(n, par.a, par.b, np.eye(4), rng[1], rng[2])[COLUNAS_ITENS].to_numpy()
    return X, polos(escores(X))


def test_formato_e_intervalo_da_saida():
    X, p = _dados(200, 0)
    modelo = clf.ClassificadorParcial((32,))
    prob = clf.prever_proba(modelo, X, np.ones_like(X, dtype=bool))
    assert prob.shape == (200, 4) and (prob >= 0).all() and (prob <= 1).all()


def test_aprende_o_ils_com_todas_as_respostas(tmp_path):
    # Com as 44 respostas, o polo é o sinal de uma soma: o MLP deve acertar quase tudo
    X, p = _dados(6000, 1)
    Xv, pv = _dados(1500, 2)
    modelo, hist = clf.treinar(X, p, Xv, pv, CFG, seed=0, log=lambda *_: None)
    assert hist[-1]["perda_treino"] < hist[0]["perda_treino"]
    prob = clf.prever_proba(modelo, Xv, np.ones_like(Xv, dtype=bool))
    assert ((prob >= 0.5) == (pv == 1)).mean() > 0.95

    # salvar e carregar devolve o mesmo modelo
    clf.salvar(modelo, tmp_path / "m.pt")
    de_novo = clf.carregar(tmp_path / "m.pt")
    assert np.allclose(clf.prever_proba(de_novo, Xv, np.ones_like(Xv, dtype=bool)), prob)


def test_treino_reproduzivel_com_mesma_seed():
    X, p = _dados(1500, 3)
    cfg = {**CFG, "max_epocas": 2}
    m1, _ = clf.treinar(X, p, X[:300], p[:300], cfg, seed=7, log=lambda *_: None)
    m2, _ = clf.treinar(X, p, X[:300], p[:300], cfg, seed=7, log=lambda *_: None)
    tudo = np.ones_like(X, dtype=bool)
    assert np.allclose(clf.prever_proba(m1, X, tudo), clf.prever_proba(m2, X, tudo))
