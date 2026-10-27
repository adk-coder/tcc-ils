"""Modelo logístico de dois parâmetros (2PL) da Teoria de Resposta ao Item.

    P(resposta = "a" | θ) = 1 / (1 + exp(−a_i · (θ − b_i)))

θ   : traço latente do respondente na dimensão (quanto mais alto, mais
      inclinado ao polo "a": ativo, sensorial, visual, sequencial).
a_i : discriminação do item — quão bem ele separa quem tem θ alto de quem
      tem θ baixo. a_i perto de 0 = item quase aleatório.
b_i : localização ("dificuldade") — o θ em que a chance de responder "a" é 50%.
"""

import numpy as np

# Constante que aproxima a curva logística da curva normal acumulada
# (logística(1,702·x) ≈ Φ(x)). Valor clássico da TRI.
D = 1.702


def prob_a(theta: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Probabilidade de responder "a".

    theta: (n,) ; a, b: (k,)  →  retorna (n, k)
    """
    theta = np.asarray(theta)[:, None]
    return 1.0 / (1.0 + np.exp(-np.asarray(a)[None, :] * (theta - np.asarray(b)[None, :])))


def informacao_fisher(theta: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Informação de Fisher do item no 2PL: I(θ) = a² · P · (1 − P).

    Será usada no TAC (etapa 3) para escolher o próximo item.
    """
    p = prob_a(theta, a, b)
    return (np.asarray(a)[None, :] ** 2) * p * (1.0 - p)
