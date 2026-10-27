"""Cálculo do resultado do ILS a partir das 44 respostas.

Este é o "gabarito" do trabalho: o resultado que o questionário adaptativo
precisa reproduzir.

    escore da dimensão = (nº de respostas "a") − (nº de respostas "b")

Com 11 itens, se k respostas forem "a", então escore = k − (11 − k) = 2k − 11.
Como 2k é par e 11 é ímpar, o escore é sempre ímpar (−11, −9, ..., +9, +11):
nunca há empate, sempre existe um polo.
"""

import numpy as np

from .constantes import ITENS_POR_DIMENSAO, N_DIMENSOES, N_ITENS, itens_da_dimensao

# Faixas de intensidade pelo valor absoluto do escore
LEVE, MODERADA, FORTE = 0, 1, 2
NOMES_INTENSIDADE = {LEVE: "leve", MODERADA: "moderada", FORTE: "forte"}


def escores(respostas: np.ndarray) -> np.ndarray:
    """Escore de cada dimensão.

    respostas: matriz (n_respondentes, 44) com 1 = "a" e 0 = "b".
    retorna:   matriz (n_respondentes, 4) de inteiros ímpares em [-11, 11].
    """
    respostas = np.asarray(respostas)
    if respostas.shape[1] != N_ITENS:
        raise ValueError(f"esperava {N_ITENS} colunas, recebi {respostas.shape[1]}")
    saida = np.empty((respostas.shape[0], N_DIMENSOES), dtype=np.int8)
    for d in range(N_DIMENSOES):
        colunas = [i - 1 for i in itens_da_dimensao(d)]  # itens 1..44 → índices 0..43
        n_a = respostas[:, colunas].sum(axis=1)
        saida[:, d] = 2 * n_a - ITENS_POR_DIMENSAO
    return saida


def polos(escore: np.ndarray) -> np.ndarray:
    """Polo: 1 se escore > 0 (polo da resposta "a"), 0 caso contrário."""
    return (np.asarray(escore) > 0).astype(np.int8)


def intensidades(escore: np.ndarray) -> np.ndarray:
    """Faixa de intensidade: leve (1–3), moderada (5–7), forte (9–11)."""
    absoluto = np.abs(np.asarray(escore))
    return np.select([absoluto <= 3, absoluto <= 7], [LEVE, MODERADA], default=FORTE).astype(np.int8)
