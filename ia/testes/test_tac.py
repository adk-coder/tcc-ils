"""Testes da etapa 3 (TAC). Rodar com:  pytest testes/"""

import numpy as np
import pytest

from ils_adaptativo.calibracao import calibrar
from ils_adaptativo.constantes import N_ITENS, itens_da_dimensao
from ils_adaptativo.escore import escores, polos
from ils_adaptativo.gerador import gerar_respondentes
from ils_adaptativo.tac import TAC


def _dados(n=3000, seed=0):
    rng = [np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(3)]
    par = calibrar(np.full(N_ITENS, 0.4), np.full(N_ITENS, 0.5), "item_resto", rng[0],
                   n_amostra=3000, max_iteracoes=8)
    df = gerar_respondentes(n, par.a, par.b, np.eye(4), rng[1], rng[2])
    return df[[f"q{i:02d}" for i in range(1, 45)]].to_numpy(), par


def _tac_com_parametros_verdadeiros(par):
    # Evita rodar o girth em todo teste: usa os parâmetros do gerador
    tac = TAC()
    tac.a, tac.b = par.a.copy(), par.b.copy()
    return tac


def test_girth_recupera_as_discriminacoes():
    pytest.importorskip("girth")
    X, par = _dados(n=8000)
    tac = TAC().ajustar(X)
    # todos os itens do gerador de teste têm a ≈ 1,2; o girth deve chegar perto
    assert np.abs(tac.a - par.a).max() < 0.25


def test_limiar_maximo_reproduz_o_ils():
    # Exigindo certeza, o alvo "escore" só para quando o polo está decidido → 100% de acerto
    X, par = _dados()
    tac = _tac_com_parametros_verdadeiros(par)
    p = polos(escores(X))
    for d in range(4):
        r = TAC.aplicar_limiar(tac.trajetoria(X, d), 1 - 1e-9, "escore")
        assert (r["polo"] == p[:, d]).all()
        assert r["n_questoes"].min() >= 6


def test_mais_limiar_mais_questoes():
    X, par = _dados()
    traj = _tac_com_parametros_verdadeiros(par).trajetoria(X, 0)
    q = [TAC.aplicar_limiar(traj, lim)["n_questoes"].mean() for lim in (0.7, 0.8, 0.9, 0.95)]
    assert q == sorted(q)


def test_proxima_questao_concorda_com_a_simulacao():
    # Pergunta a pergunta (como na plataforma) dá o mesmo resultado que a simulação vetorizada
    X, par = _dados(n=300)
    tac = _tac_com_parametros_verdadeiros(par)
    for d in range(4):
        traj = tac.trajetoria(X, d)
        r = TAC.aplicar_limiar(traj, 0.9)
        for aluno in range(100):
            respondidas = {}
            while True:
                item, polo, _ = tac.proxima_questao(d, respondidas, 0.9)
                if item is None:
                    break
                respondidas[item] = int(X[aluno, item - 1])
            assert polo == r["polo"][aluno]
            assert len(respondidas) == r["n_questoes"][aluno]
            assert list(respondidas) == list(traj["ordem"][aluno, :len(respondidas)])


def test_selecao_igual_ao_maxinfo_do_catsim():
    pytest.importorskip("catsim")
    from catsim.item_bank import ItemBank
    from catsim.selection import MaxInfoSelector

    _, par = _dados(n=500)
    tac = _tac_com_parametros_verdadeiros(par)
    idx = [i - 1 for i in itens_da_dimensao(0)]
    banco = ItemBank(np.c_[par.a[idx], par.b[idx]])
    rng = np.random.default_rng(0)
    for _ in range(50):
        theta = rng.normal()
        feitos = sorted(rng.choice(11, size=rng.integers(0, 10), replace=False).tolist())
        info = tac._informacao(np.array([theta]), idx)[0]
        info[feitos] = -np.inf
        # argumentos por nome: no catsim 0.21.0 o 1º parâmetro posicional é `index`
        escolhido = MaxInfoSelector().select(item_bank=banco, administered_items=feitos, est_theta=theta)
        assert int(info.argmax()) == escolhido
