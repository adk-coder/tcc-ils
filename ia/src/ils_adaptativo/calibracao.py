"""Calibração dos parâmetros do gerador a partir de dados publicados.

PROBLEMA: os artigos sobre o ILS não publicam parâmetros de TRI (a_i, b_i);
publicam estatísticas clássicas: a correlação item-total corrigida de cada
item (Litzinger et al., 2005) e as correlações entre os escores das escalas
(Felder e Spurlin, 2005). Precisamos escolher os parâmetros do gerador de modo
que os DADOS GERADOS tenham essas mesmas estatísticas.

PARTE A — itens (a_i, b_i), em duas etapas:

1) Chute inicial por fórmula fechada (modelo de variável latente):
   imagine que cada resposta vem de uma variável contínua y* = λ·θ + ruído,
   e o aluno marca "a" quando y* passa de um limiar τ. Nesse modelo:
       a_i = D · λ_i / sqrt(1 − λ_i²)        (D = 1,702, ver irt.py)
       b_i = Φ⁻¹(1 − p_i) / λ_i
   e usamos λ_i ≈ r_i. Essa aproximação é imperfeita (correlação item-total
   não é exatamente a carga λ), por isso existe a etapa 2.

2) Ajuste numérico por simulação:
   gera uma amostra de calibração, mede r_i e p_i simulados e corrige:
       a_i ← a_i · (r_alvo / r_simulado)      (aumenta a se a correlação ficou baixa)
       b_i ← b_i + [logit(p_sim) − logit(p_alvo)] / a_i
   repetindo até as diferenças ficarem abaixo da tolerância.
   Os mesmos números aleatórios são reutilizados em todas as iterações
   ("números aleatórios comuns"), então o processo é determinístico e só os
   parâmetros mudam entre uma iteração e outra.

   Itens com correlação publicada muito baixa ou negativa (ex.: item 40,
   r = −0,0105) são modelados com r_minimo: um item quase sem discriminação,
   que se comporta praticamente como "cara ou coroa". Um 2PL com a > 0 não
   gera correlação negativa, e o valor publicado é estatisticamente
   indistinguível de zero.

PARTE B — correlação entre as dimensões:
   A correlação entre θ de duas dimensões não é igual à correlação entre os
   escores observados (o erro de medida "dilui" a correlação). Por isso,
   procuramos por bissecção o ρ entre os θ que faz a correlação entre os
   ESCORES simulados bater com a publicada.
"""

from dataclasses import dataclass

import numpy as np
from scipy.special import logit
from scipy.stats import norm

from .constantes import DIMENSOES, ITENS_POR_DIMENSAO, N_DIMENSOES, N_ITENS, itens_da_dimensao
from .irt import D, prob_a


@dataclass
class ParametrosItens:
    a: np.ndarray            # (44,) discriminação
    b: np.ndarray            # (44,) localização
    r_alvo: np.ndarray       # (44,) correlação publicada (valor original)
    r_usado: np.ndarray      # (44,) alvo efetivo (após aplicar r_minimo)
    p_alvo: np.ndarray       # (44,) proporção de "a" usada
    r_obtido: np.ndarray     # (44,) correlação na amostra de calibração
    p_obtido: np.ndarray     # (44,) proporção na amostra de calibração
    iteracoes: int
    convergiu: bool


def correlacoes_itens(respostas: np.ndarray, tipo: str) -> np.ndarray:
    """Correlação de cada item com o escore da própria dimensão.

    tipo = "item_resto": item × soma dos outros itens da dimensão (corrigida)
    tipo = "item_total": item × soma de todos os itens da dimensão
    """
    r = np.empty(N_ITENS)
    for d in range(N_DIMENSOES):
        idx = [i - 1 for i in itens_da_dimensao(d)]
        bloco = respostas[:, idx].astype(float)
        total = bloco.sum(axis=1)
        for j, coluna in enumerate(idx):
            referencia = total - bloco[:, j] if tipo == "item_resto" else total
            r[coluna] = np.corrcoef(bloco[:, j], referencia)[0, 1]
    return r


def _simular(theta: np.ndarray, uniformes: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Gera respostas 0/1 com θ e uniformes FIXOS (números aleatórios comuns)."""
    respostas = np.empty(uniformes.shape, dtype=np.int8)
    for d in range(N_DIMENSOES):
        idx = [i - 1 for i in itens_da_dimensao(d)]
        p = prob_a(theta[:, d], a[idx], b[idx])
        respostas[:, idx] = (uniformes[:, idx] < p).astype(np.int8)
    return respostas


def calibrar(
    r_alvo: np.ndarray,
    p_alvo: np.ndarray,
    tipo_correlacao: str,
    rng: np.random.Generator,
    n_amostra: int = 50_000,
    max_iteracoes: int = 30,
    tolerancia: float = 0.002,
    a_maximo: float = 4.0,
    r_minimo: float = 0.02,
) -> ParametrosItens:
    """Parte A: calibra a_i e b_i.

    As estatísticas de item dependem só da própria dimensão, então aqui os
    θ podem ser sorteados independentes (a correlação entre dimensões é
    tratada depois, em calibrar_correlacao_tracos).
    """
    r_alvo = np.asarray(r_alvo, dtype=float)
    p_alvo = np.asarray(p_alvo, dtype=float)
    if np.any(np.abs(r_alvo) >= 1):
        raise ValueError("correlações-alvo devem estar entre −1 e 1")
    if np.any((p_alvo <= 0) | (p_alvo >= 1)):
        raise ValueError("todas as proporções-alvo devem estar entre 0 e 1")
    r_usado = np.maximum(r_alvo, r_minimo)

    # --- Etapa 1: chute inicial por fórmula fechada ---
    lam = np.clip(r_usado, 0.02, 0.95)
    a = np.minimum(D * lam / np.sqrt(1 - lam**2), a_maximo)
    b = norm.ppf(1 - p_alvo) / lam

    # Amostra de calibração: sorteada uma única vez
    theta = rng.standard_normal((n_amostra, N_DIMENSOES))
    uniformes = rng.random((n_amostra, N_ITENS))

    # --- Etapa 2: ajuste numérico ---
    convergiu = False
    for iteracao in range(1, max_iteracoes + 1):
        resp = _simular(theta, uniformes, a, b)
        r_sim = correlacoes_itens(resp, tipo_correlacao)
        p_sim = np.clip(resp.mean(axis=0), 1e-4, 1 - 1e-4)

        if np.abs(r_sim - r_usado).max() < tolerancia and np.abs(p_sim - p_alvo).max() < tolerancia:
            convergiu = True
            break

        a = np.clip(a * r_usado / np.maximum(r_sim, 1e-3), 0.01, a_maximo)
        b = b + (logit(p_sim) - logit(p_alvo)) / a

    resp = _simular(theta, uniformes, a, b)
    return ParametrosItens(
        a=a, b=b, r_alvo=r_alvo, r_usado=r_usado, p_alvo=p_alvo,
        r_obtido=correlacoes_itens(resp, tipo_correlacao),
        p_obtido=resp.mean(axis=0),
        iteracoes=iteracao, convergiu=convergiu,
    )


def _escore_dimensao(theta_d, unif, a, b):
    """Escore (2·nº de "a" − 11) de uma dimensão, para θ e uniformes dados."""
    return 2 * (unif < prob_a(theta_d, a, b)).sum(axis=1) - ITENS_POR_DIMENSAO


def calibrar_correlacao_tracos(
    a: np.ndarray,
    b: np.ndarray,
    alvos: dict[str, float],
    rng: np.random.Generator,
    n_amostra: int = 50_000,
    tolerancia: float = 0.002,
) -> tuple[np.ndarray, dict]:
    """Parte B: encontra a matriz de correlação Σ entre os θ.

    alvos: {"sen_int-seq_glo": 0.44, ...} — correlação desejada entre os
           ESCORES das duas dimensões. Pares não listados ficam com ρ = 0.
    retorna: (Σ 4×4, relatório {par: {alvo, rho_theta, obtido}})
    """
    sigma = np.eye(N_DIMENSOES)
    relatorio = {}
    for par, alvo in alvos.items():
        d1, d2 = (DIMENSOES.index(n) for n in par.split("-"))
        idx1 = [i - 1 for i in itens_da_dimensao(d1)]
        idx2 = [i - 1 for i in itens_da_dimensao(d2)]
        z = rng.standard_normal((n_amostra, 2))
        u1 = rng.random((n_amostra, ITENS_POR_DIMENSAO))
        u2 = rng.random((n_amostra, ITENS_POR_DIMENSAO))

        def corr_escores(rho):
            # θ2 = ρ·θ1 + sqrt(1−ρ²)·ruído  →  corr(θ1, θ2) = ρ
            t1 = z[:, 0]
            t2 = rho * z[:, 0] + np.sqrt(1 - rho**2) * z[:, 1]
            e1 = _escore_dimensao(t1, u1, a[idx1], b[idx1])
            e2 = _escore_dimensao(t2, u2, a[idx2], b[idx2])
            return np.corrcoef(e1, e2)[0, 1]

        # Bissecção: a correlação dos escores cresce com ρ
        baixo, alto = (0.0, 0.999) if alvo >= 0 else (-0.999, 0.0)
        for _ in range(40):
            meio = (baixo + alto) / 2
            if corr_escores(meio) < alvo:
                baixo = meio
            else:
                alto = meio
            if alto - baixo < 1e-4:
                break
        rho = (baixo + alto) / 2
        obtido = corr_escores(rho)
        if abs(obtido - alvo) > max(tolerancia, 0.01):
            raise ValueError(f"não foi possível atingir correlação {alvo} para {par} (obtido {obtido:.3f})")
        sigma[d1, d2] = sigma[d2, d1] = rho
        relatorio[par] = {"alvo_escores": alvo, "rho_theta": round(float(rho), 4),
                          "obtido_escores": round(float(obtido), 4)}

    if np.linalg.eigvalsh(sigma).min() <= 0:
        raise ValueError("a matriz de correlação resultante não é positiva definida")
    return sigma, relatorio
