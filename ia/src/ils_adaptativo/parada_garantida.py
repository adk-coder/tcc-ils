"""Referência sem IA: "parada garantida".

Em cada dimensão, pergunta os itens numa ordem fixa e PARA assim que o polo
estiver matematicamente decidido, ou seja, quando um dos lados juntar 6
respostas (6 de 11 já garantem o sinal do escore, não importa o resto).

- Acurácia do polo: sempre 100% (não é previsão, é certeza).
- Nº de questões: entre 6 e 11 por dimensão.
- Não decide a INTENSIDADE (para isso precisaria das 11 respostas).

Por que isso importa: é o "adversário honesto" das abordagens com IA. Qualquer
modelo que aceite errar (meta de 90%) precisa usar CLARAMENTE menos questões
do que esta regra; senão, não compensa errar.

Ordem dos itens: decrescente pela correlação item-resto medida no TREINO
(itens mais discriminativos primeiro). Não usa os parâmetros do gerador.
"""

import numpy as np

from .calibracao import correlacoes_itens
from .constantes import ITENS_POR_DIMENSAO, N_DIMENSOES, itens_da_dimensao
from .escore import escores, polos

LIMIAR = ITENS_POR_DIMENSAO // 2 + 1  # 6


def ordem_por_correlacao(X_treino: np.ndarray) -> list[list[int]]:
    """Para cada dimensão, índices (0..43) dos itens do mais ao menos discriminativo."""
    r = correlacoes_itens(X_treino, "item_resto")
    return [sorted([i - 1 for i in itens_da_dimensao(d)], key=lambda c: -r[c]) for d in range(N_DIMENSOES)]


def simular(X: np.ndarray, ordem: list[list[int]]) -> dict[str, np.ndarray]:
    """Retorna polo (n, 4) e n_questoes (n, 4) da regra de parada garantida."""
    n = X.shape[0]
    n_q = np.empty((n, N_DIMENSOES), dtype=np.int16)
    for d in range(N_DIMENSOES):
        R = X[:, ordem[d]]
        n_a, n_b = np.cumsum(R, axis=1), np.cumsum(1 - R, axis=1)
        n_q[:, d] = np.argmax((n_a >= LIMIAR) | (n_b >= LIMIAR), axis=1) + 1
    return {"polo": polos(escores(X)), "n_questoes": n_q}
