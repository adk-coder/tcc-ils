"""Avaliação de classificadores de respostas parciais (só numpy).

Funciona para qualquer "função de probabilidade" prob(X, mascara) -> (n, 4),
seja o MLP ou o TAC. Assim os dois são comparados exatamente do mesmo jeito.
"""

import numpy as np

from .constantes import DIMENSOES, ITENS_POR_DIMENSAO, N_DIMENSOES
from .mascaras import mascara_k_itens


def ece(prob: np.ndarray, real: np.ndarray, n_faixas: int = 10) -> float:
    """Erro de calibração esperado (ECE) de uma previsão binária.

    Agrupa os alunos pela confiança (0,5 a 1) e compara, em cada grupo, a
    confiança média com a acurácia real. Um modelo bem calibrado que diz "90%"
    acerta 90% das vezes. Isso importa porque a parada (TAC e RL) confia nessas
    probabilidades.
    """
    confianca = np.maximum(prob, 1 - prob)
    acerto = (prob >= 0.5) == (real == 1)
    faixas = np.minimum(((confianca - 0.5) / 0.5 * n_faixas).astype(int), n_faixas - 1)
    total = 0.0
    for f in range(n_faixas):
        sel = faixas == f
        if sel.any():
            total += sel.mean() * abs(confianca[sel].mean() - acerto[sel].mean())
    return float(total)


def log_loss(prob: np.ndarray, real: np.ndarray) -> float:
    p = np.clip(prob, 1e-7, 1 - 1e-7)
    return float(-np.mean(real * np.log(p) + (1 - real) * np.log(1 - p)))


def resumo_por_dimensao(prob: np.ndarray, polo: np.ndarray) -> dict:
    """Acurácia, log-loss e ECE por dimensão. prob e polo: (n, 4)."""
    return {nome: {"acuracia": round(float(((prob[:, d] >= 0.5) == (polo[:, d] == 1)).mean()), 4),
                   "log_loss": round(log_loss(prob[:, d], polo[:, d]), 4),
                   "ece": round(ece(prob[:, d], polo[:, d]), 4)}
            for d, nome in enumerate(DIMENSOES)}


def curva_k_itens(prob_fns: dict, X: np.ndarray, polo: np.ndarray, seed: int) -> list[dict]:
    """Acurácia do polo da dimensão d sabendo exatamente k itens dela (k = 0..11).

    prob_fns: {"rotulo": (funcao(X, mascara) -> (n, 4), outras)}, em que
              outras = "nenhuma" ou "todas" (itens das OUTRAS dimensões).
    A mesma semente gera as mesmas máscaras para todos os modelos.
    """
    linhas = []
    for d, nome in enumerate(DIMENSOES):
        for k in range(ITENS_POR_DIMENSAO + 1):
            for rotulo, (fn, outras) in prob_fns.items():
                rng = np.random.default_rng([seed, d, k])
                mascara = mascara_k_itens(len(X), d, k, rng, outras)
                p = fn(X, mascara)[:, d]
                linhas.append({"modelo": rotulo, "dimensao": nome, "k": k,
                               "acuracia": float(((p >= 0.5) == (polo[:, d] == 1)).mean()),
                               "log_loss": log_loss(p, polo[:, d])})
    return linhas


def prob_tac(tac):
    """Adapta o TAC ao formato prob(X, mascara) -> (n, 4)."""
    return lambda X, m: np.stack([tac.prob_polo_mascara(X, m, d) for d in range(N_DIMENSOES)], axis=1)
