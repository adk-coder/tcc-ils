"""Respostas parciais: máscaras e codificação da entrada do classificador (abordagem 3).

Durante o questionário adaptativo, o classificador vê só PARTE das 44 respostas.
Para treiná-lo, simulamos esses estados parciais "escondendo" respostas de
alunos completos (máscara = quais itens já foram respondidos).

CODIFICAÇÃO (88 números por aluno):
  - 44 "foi perguntado?" (1 = sim, 0 = não)
  - 44 "resposta": +1 = "a", −1 = "b", 0 = ainda não perguntado
A primeira metade é necessária porque, sem ela, "não perguntado" e uma
resposta neutra seriam indistinguíveis.

SORTEIO DAS MÁSCARAS ("por_dimensao"): para cada aluno e cada dimensão,
sorteia quantos itens já foram respondidos (0 a 11, uniforme) e quais.
Assim o classificador aprende estados como "7 itens de ativo/reflexivo, 2 de
visual/verbal e nenhum das outras" — o tipo de estado que a política de RL vai
produzir, em que as dimensões avançam em ritmos diferentes.
"""

import numpy as np

from .constantes import N_DIMENSOES, N_ITENS, itens_da_dimensao

N_ENTRADAS = 2 * N_ITENS


def sortear_mascaras(n: int, rng: np.random.Generator) -> np.ndarray:
    """(n, 44) booleana: True = item já respondido."""
    mascara = np.zeros((n, N_ITENS), dtype=bool)
    for d in range(N_DIMENSOES):
        idx = np.array([i - 1 for i in itens_da_dimensao(d)])
        k = rng.integers(0, len(idx) + 1, size=n)                 # quantos respondidos
        # ordem aleatória dos itens da dimensão para cada aluno; pega os k primeiros
        ordem = np.argsort(rng.random((n, len(idx))), axis=1)
        escolhidos = np.arange(len(idx))[None, :] < k[:, None]
        linhas = np.repeat(np.arange(n), len(idx))
        mascara[linhas, idx[ordem].ravel()] = escolhidos.ravel()
    return mascara


def mascara_k_itens(n: int, d: int, k: int, rng: np.random.Generator,
                    outras: str = "nenhuma") -> np.ndarray:
    """Máscara com exatamente k itens da dimensão d.

    outras = "nenhuma": nenhum item das outras dimensões respondido
    outras = "todas":   todos os itens das outras dimensões respondidos
    (usada para medir quanto as outras dimensões ajudam a prever d)
    """
    mascara = np.zeros((n, N_ITENS), dtype=bool)
    if outras == "todas":
        mascara[:] = True
    idx = np.array([i - 1 for i in itens_da_dimensao(d)])
    mascara[:, idx] = False
    ordem = np.argsort(rng.random((n, len(idx))), axis=1)[:, :k]
    mascara[np.repeat(np.arange(n), k), idx[ordem].ravel()] = True
    return mascara


def codificar(X: np.ndarray, mascara: np.ndarray) -> np.ndarray:
    """(n, 88) float32: [foi perguntado (44) | resposta ±1 ou 0 (44)]."""
    valor = np.where(mascara, 2 * X.astype(np.float32) - 1, 0.0).astype(np.float32)
    return np.concatenate([mascara.astype(np.float32), valor], axis=1)
