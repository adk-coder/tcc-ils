"""Testes da etapa 1. Rodar com:  pytest testes/"""

import numpy as np
import pandas as pd

from ils_adaptativo.calibracao import calibrar
from ils_adaptativo.constantes import COLUNAS_ITENS, N_ITENS, dimensao_do_item, itens_da_dimensao
from ils_adaptativo.escore import FORTE, LEVE, MODERADA, escores, intensidades, polos
from ils_adaptativo.gerador import dividir, gerar_respondentes


def test_mapeamento_itens():
    assert itens_da_dimensao(0) == [1, 5, 9, 13, 17, 21, 25, 29, 33, 37, 41]
    assert itens_da_dimensao(3)[-1] == 44
    assert all(len(itens_da_dimensao(d)) == 11 for d in range(4))
    assert dimensao_do_item(2) == 1


def test_escore_extremos_e_impar():
    todas_a = np.ones((1, N_ITENS), dtype=int)
    todas_b = np.zeros((1, N_ITENS), dtype=int)
    assert (escores(todas_a) == 11).all()
    assert (escores(todas_b) == -11).all()
    aleatorias = np.random.default_rng(0).integers(0, 2, size=(1000, N_ITENS))
    assert (escores(aleatorias) % 2 != 0).all()  # sempre ímpar → sempre há polo


def test_escore_exemplo_manual():
    # dimensão 0 com 6 respostas "a" e 5 "b" → 6 − 5 = +1 (ativo, leve)
    r = np.zeros((1, N_ITENS), dtype=int)
    for item in itens_da_dimensao(0)[:6]:
        r[0, item - 1] = 1
    e = escores(r)
    assert e[0, 0] == 1 and polos(e)[0, 0] == 1 and intensidades(e)[0, 0] == LEVE


def test_faixas_intensidade():
    e = np.array([-11, -9, -7, -5, -3, -1, 1, 3, 5, 7, 9, 11])
    esperado = [FORTE, FORTE, MODERADA, MODERADA, LEVE, LEVE, LEVE, LEVE, MODERADA, MODERADA, FORTE, FORTE]
    assert intensidades(e).tolist() == esperado


def _gerar(seed):
    sigma = np.eye(4)
    rng = [np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(3)]
    par = calibrar(np.full(N_ITENS, 0.4), np.full(N_ITENS, 0.5), "item_resto", rng[0],
                   n_amostra=5000, max_iteracoes=10)
    return gerar_respondentes(2000, par.a, par.b, sigma, rng[1], rng[2])


def test_reprodutibilidade_com_mesma_seed():
    pd.testing.assert_frame_equal(_gerar(42), _gerar(42))
    assert not _gerar(42).equals(_gerar(43))


def test_divisao_sem_sobreposicao():
    df = _gerar(1)
    partes = dividir(df, {"treino": 0.7, "validacao": 0.15, "teste": 0.15}, np.random.default_rng(0))
    ids = [set(p["id"]) for p in partes.values()]
    assert sum(len(s) for s in ids) == len(df)
    assert not (ids[0] & ids[1]) and not (ids[0] & ids[2]) and not (ids[1] & ids[2])


def test_gabarito_bate_com_respostas():
    df = _gerar(7)
    recalculado = escores(df[COLUNAS_ITENS].to_numpy())
    assert (recalculado[:, 0] == df["escore_ati_ref"].to_numpy()).all()


def test_item_com_correlacao_negativa_vai_para_o_piso():
    r = np.full(N_ITENS, 0.4)
    r[39] = -0.0105  # item 40
    par = calibrar(r, np.full(N_ITENS, 0.5), "item_resto", np.random.default_rng(0),
                   n_amostra=5000, max_iteracoes=10, r_minimo=0.02)
    assert par.r_usado[39] == 0.02 and par.a[39] < 0.3


def test_calibracao_correlacao_entre_dimensoes():
    from ils_adaptativo.calibracao import calibrar_correlacao_tracos
    par = calibrar(np.full(N_ITENS, 0.4), np.full(N_ITENS, 0.5), "item_resto", np.random.default_rng(0),
                   n_amostra=5000, max_iteracoes=10)
    sigma, rel = calibrar_correlacao_tracos(par.a, par.b, {"sen_int-seq_glo": 0.44},
                                            np.random.default_rng(1), n_amostra=20000)
    assert abs(rel["sen_int-seq_glo"]["obtido_escores"] - 0.44) < 0.01
    assert sigma[1, 3] > 0.44  # ρ entre os θ é maior que entre os escores (atenuação)
