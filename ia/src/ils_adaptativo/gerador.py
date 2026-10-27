"""Geração dos respondentes sintéticos.

Passos para cada respondente:
  1. sorteia θ = (θ_ati_ref, θ_sen_int, θ_vis_ver, θ_seq_glo) ~ Normal(0, Σ);
  2. para cada item i, calcula P(a) pelo 2PL com os a_i, b_i calibrados;
  3. sorteia a resposta: "a" (1) com probabilidade P(a), senão "b" (0);
  4. calcula escore, polo e intensidade sobre as 44 respostas → GABARITO.

Importante para a banca: o gabarito NÃO é o sinal de θ, e sim o resultado do
ILS completo calculado sobre as respostas geradas. É exatamente isso que o
questionário adaptativo precisa reproduzir. θ é salvo só para análises
(ex.: "onde o modelo erra?"), e é PROIBIDO usá-lo como entrada dos modelos.
"""

import numpy as np
import pandas as pd

from .constantes import COLUNAS_ITENS, DIMENSOES, N_DIMENSOES, itens_da_dimensao
from .escore import escores, intensidades, polos
from .irt import prob_a


def gerar_respondentes(
    n: int,
    a: np.ndarray,
    b: np.ndarray,
    correlacao_tracos: np.ndarray,
    rng_theta: np.random.Generator,
    rng_respostas: np.random.Generator,
) -> pd.DataFrame:
    theta = rng_theta.multivariate_normal(np.zeros(N_DIMENSOES), correlacao_tracos, size=n)

    respostas = np.empty((n, len(COLUNAS_ITENS)), dtype=np.int8)
    uniformes = rng_respostas.random(respostas.shape)
    for d in range(N_DIMENSOES):
        idx = [i - 1 for i in itens_da_dimensao(d)]
        p = prob_a(theta[:, d], a[idx], b[idx])
        respostas[:, idx] = (uniformes[:, idx] < p).astype(np.int8)

    esc = escores(respostas)
    df = pd.DataFrame(respostas, columns=COLUNAS_ITENS)
    df.insert(0, "id", np.arange(n, dtype=np.int32))
    for d, nome in enumerate(DIMENSOES):
        df[f"escore_{nome}"] = esc[:, d]
        df[f"polo_{nome}"] = polos(esc[:, d])
        df[f"intensidade_{nome}"] = intensidades(esc[:, d])
    for d, nome in enumerate(DIMENSOES):
        # prefixo "oculto_" deixa explícito que não é entrada de modelo
        df[f"oculto_theta_{nome}"] = theta[:, d].astype(np.float32)
    return df


def dividir(df: pd.DataFrame, proporcoes: dict, rng: np.random.Generator) -> dict[str, pd.DataFrame]:
    """Embaralha e divide em treino / validação / teste.

    Como os respondentes são independentes e identicamente distribuídos,
    uma divisão aleatória simples já mantém a mesma distribuição nos três
    conjuntos (o script confere isso nas métricas).
    """
    if abs(sum(proporcoes.values()) - 1.0) > 1e-9:
        raise ValueError("as proporções da divisão devem somar 1")
    ordem = rng.permutation(len(df))
    n_treino = int(round(proporcoes["treino"] * len(df)))
    n_val = int(round(proporcoes["validacao"] * len(df)))
    partes = {
        "treino": ordem[:n_treino],
        "validacao": ordem[n_treino:n_treino + n_val],
        "teste": ordem[n_treino + n_val:],
    }
    return {nome: df.iloc[idx].sort_values("id").reset_index(drop=True) for nome, idx in partes.items()}


def alfa_cronbach(bloco: np.ndarray) -> float:
    """Alfa de Cronbach de um conjunto de itens (consistência interna)."""
    k = bloco.shape[1]
    var_itens = bloco.var(axis=0, ddof=1).sum()
    var_total = bloco.sum(axis=1).var(ddof=1)
    return float(k / (k - 1) * (1 - var_itens / var_total))
