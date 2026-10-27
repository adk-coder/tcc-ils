"""Métricas de avaliação, COMUNS às três abordagens (árvore, TAC, RL).

Usar sempre esta mesma função garante que as três abordagens são comparadas
exatamente do mesmo jeito no capítulo de Resultados.

Métricas:
- acurácia do polo por dimensão (critério de sucesso: ≥ 0,90 em todas);
- Kappa de Cohen do polo (acerto descontado do acaso; com polos ~50/50,
  Kappa ≈ 2·acurácia − 1);
- número médio de questões (por dimensão e total);
- concordância na faixa de intensidade (métrica secundária);
- acurácia do polo separada por faixa de intensidade do gabarito, para
  mostrar ONDE o modelo erra (espera-se erro concentrado na faixa leve).
"""

import numpy as np
from sklearn.metrics import cohen_kappa_score

from .constantes import DIMENSOES
from .escore import NOMES_INTENSIDADE


def avaliar(
    polo_real: np.ndarray,
    polo_prev: np.ndarray,
    n_questoes: np.ndarray,
    intensidade_real: np.ndarray | None = None,
    intensidade_prev: np.ndarray | None = None,
    n_total: np.ndarray | None = None,
) -> dict:
    """Todas as matrizes têm forma (n, 4).

    n_questoes[i, d] = quantas questões o respondente i viu PARA DECIDIR a dimensão d.
    n_total[i]       = total de questões DISTINTAS que o respondente i viu.
                       Se omitido, usa a soma de n_questoes (correto quando
                       cada questão serve a uma única dimensão). Quando um
                       mesmo item ajuda várias dimensões, passe a contagem
                       real aqui para não contar a mesma questão duas vezes.
    """
    if n_total is None:
        n_total = n_questoes.sum(axis=1)
    saida = {"por_dimensao": {}}
    for d, nome in enumerate(DIMENSOES):
        real, prev = polo_real[:, d], polo_prev[:, d]
        m = {
            "acuracia_polo": round(float((real == prev).mean()), 4),
            "kappa_polo": round(float(cohen_kappa_score(real, prev)), 4),
            "media_questoes": round(float(n_questoes[:, d].mean()), 3),
        }
        if intensidade_real is not None:
            m["acuracia_polo_por_faixa"] = {
                NOMES_INTENSIDADE[k]: round(float((real == prev)[intensidade_real[:, d] == k].mean()), 4)
                for k in NOMES_INTENSIDADE
            }
            if intensidade_prev is not None:
                # concorda na faixa = acerta o polo E a intensidade
                acerto = (real == prev) & (intensidade_real[:, d] == intensidade_prev[:, d])
                m["acuracia_polo_e_faixa"] = round(float(acerto.mean()), 4)
        saida["por_dimensao"][nome] = m

    acuracias = [v["acuracia_polo"] for v in saida["por_dimensao"].values()]
    saida["geral"] = {
        "acuracia_polo_media": round(float(np.mean(acuracias)), 4),
        "acuracia_polo_minima": round(float(np.min(acuracias)), 4),
        "todas_dimensoes_ge_90": bool(np.min(acuracias) >= 0.90),
        "media_questoes_total": round(float(n_total.mean()), 3),
        "desvio_questoes_total": round(float(n_total.std()), 3),
    }
    return saida
