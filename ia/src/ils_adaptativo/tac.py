"""Abordagem 2: Teste Adaptativo Computadorizado (TAC) clássico, com TRI.

COMO FUNCIONA (uma dimensão por vez, de forma independente):
  1. Calibração: estima a_i e b_i do 2PL de cada item a partir das respostas
     do TREINO, com a biblioteca girth (máxima verossimilhança marginal).
     Atenção: o TAC NÃO usa os parâmetros do gerador; ele estima os seus
     próprios a partir dos dados, como faria com dados reais.
  2. Estado do aluno: distribuição a posteriori de θ numa grade de pontos
     (prior Normal(0,1)). A cada resposta, multiplica pela verossimilhança
     do item (regra de Bayes). A estimativa atual é a média a posteriori (EAP).
  3. Seleção: o próximo item é o de MÁXIMA INFORMAÇÃO DE FISHER no θ estimado,
     entre os que ainda não foram feitos (mesma regra do MaxInfoSelector do
     catsim; os testes conferem que as duas escolhem o mesmo item).
  4. Parada: quando a probabilidade de um dos polos atingir o limiar
     (ex.: 95%), ou quando acabarem os 11 itens.

O QUE É "PROBABILIDADE DO POLO"? Duas opções (config `alvos`):
  - "escore" (recomendada): probabilidade de o ESCORE DO ILS COMPLETO ficar do
    lado "a", dado o que já foi respondido. Soma as respostas já dadas com a
    distribuição prevista das que faltam (pelo 2PL, integrando sobre θ).
    É exatamente o alvo do trabalho (o gabarito é o escore das 11 respostas).
    Bônus: quando o polo já está matematicamente decidido (6 iguais), essa
    probabilidade vale 1, então o TAC nunca pergunta mais que a parada garantida.
  - "theta": probabilidade de θ > 0. É o critério "de livro" da TRI, mas mede
    outra coisa: θ é o traço latente, não o resultado do questionário. Fica no
    experimento para mostrar, com números, por que o alvo importa.

SIMULAÇÃO VETORIZADA: em vez de simular aluno por aluno, todos os alunos de um
conjunto avançam juntos, uma pergunta por vez, e guardamos a probabilidade do
polo em CADA passo. Como a escolha do item não depende do limiar, uma única
passada dá o resultado para todos os limiares (a curva inteira) de uma vez.
"""

from dataclasses import dataclass, field

import numpy as np

from .constantes import ITENS_POR_DIMENSAO, N_DIMENSOES, N_ITENS, itens_da_dimensao
from .escore import intensidades

LIMIAR_DECIDIDO = ITENS_POR_DIMENSAO // 2 + 1  # 6 respostas "a" garantem o polo "a"


def estimar_2pl_girth(X_dim: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Estima (a, b) do 2PL com girth. X_dim: (n_alunos, n_itens) com 0/1."""
    from girth import twopl_mml  # importado aqui para o resto do pacote não depender do girth

    resultado = twopl_mml(X_dim.T.astype(int))  # girth espera (itens, pessoas)
    return np.asarray(resultado["Discrimination"], float), np.asarray(resultado["Difficulty"], float)


@dataclass
class TAC:
    n_grade: int = 61            # pontos da grade de θ
    theta_max: float = 4.0       # grade de −4 a +4
    a: np.ndarray = field(default=None, init=False)   # (44,) discriminações estimadas
    b: np.ndarray = field(default=None, init=False)   # (44,) localizações estimadas

    def __post_init__(self):
        self.grade = np.linspace(-self.theta_max, self.theta_max, self.n_grade)
        prior = np.exp(-0.5 * self.grade**2)
        self.log_prior = np.log(prior / prior.sum())

    # ------------------------------------------------------------------ calibração
    def ajustar(self, X_treino: np.ndarray, estimador=estimar_2pl_girth) -> "TAC":
        self.a, self.b = np.empty(N_ITENS), np.empty(N_ITENS)
        for d in range(N_DIMENSOES):
            idx = [i - 1 for i in itens_da_dimensao(d)]
            self.a[idx], self.b[idx] = estimador(X_treino[:, idx])
        return self

    # ------------------------------------------------------------------ peças
    def _p_grade(self, idx: list[int]) -> np.ndarray:
        """P(resposta "a" | θ) para cada ponto da grade e item: (G, k)."""
        return 1.0 / (1.0 + np.exp(-self.a[idx][None, :] * (self.grade[:, None] - self.b[idx][None, :])))

    def _informacao(self, theta: np.ndarray, idx: list[int]) -> np.ndarray:
        """Informação de Fisher a²·P·(1−P) de cada item no θ de cada aluno: (n, k)."""
        p = 1.0 / (1.0 + np.exp(-self.a[idx][None, :] * (theta[:, None] - self.b[idx][None, :])))
        return self.a[idx][None, :] ** 2 * p * (1 - p)

    @staticmethod
    def _dist_restantes(post: np.ndarray, p: np.ndarray, falta: np.ndarray) -> np.ndarray:
        """Distribuição prevista de QUANTAS respostas "a" virão nos itens que faltam.

        post : (n, G) posterior de θ ; p : (G, k) ; falta : (n, k) booleano
        Para cada θ da grade, a soma de respostas independentes com probabilidades
        diferentes segue uma "Poisson-binomial", calculada item a item
        (programação dinâmica). Depois integra sobre θ com o posterior.
        Retorna (n, k+1): probabilidade de 0, 1, ..., k respostas "a".
        """
        n, k = falta.shape
        dist = np.zeros((n, p.shape[0], k + 1))
        dist[:, :, 0] = 1.0
        for j in range(k):
            pj = p[None, :, j] * falta[:, j, None]          # item já feito → prob. 0 de somar
            novo = dist * (1 - pj)[:, :, None]
            novo[:, :, 1:] += dist[:, :, :-1] * pj[:, :, None]
            dist = novo
        return np.einsum("ng,ngk->nk", post, dist)

    # ------------------------------------------------------------------ simulação
    def trajetoria(self, X: np.ndarray, d: int) -> dict[str, np.ndarray]:
        """Faz as 11 perguntas da dimensão d a todos os alunos, na ordem do TAC.

        Retorna, para cada passo k = 0..11 (k perguntas já feitas):
          p_escore[k] : (n,) P(polo "a" do ILS completo | k respostas)
          p_theta[k]  : (n,) P(θ > 0 | k respostas)
          dist_na[k]  : (n, 12) distribuição prevista do nº final de respostas "a"
          ordem       : (n, 11) itens (1..44) na ordem em que foram perguntados
        """
        idx = [i - 1 for i in itens_da_dimensao(d)]
        n, k = X.shape[0], len(idx)
        p = self._p_grade(idx)
        log_p, log_q = np.log(p), np.log(1 - p)
        positivo = self.grade > 0

        log_post = np.tile(self.log_prior, (n, 1))
        falta = np.ones((n, k), dtype=bool)
        n_a = np.zeros(n, dtype=int)
        p_esc, p_th, dist_na = [], [], []
        ordem = np.empty((n, k), dtype=int)
        linhas = np.arange(n)

        for passo in range(k + 1):
            post = np.exp(log_post - log_post.max(axis=1, keepdims=True))
            post /= post.sum(axis=1, keepdims=True)

            # distribuição do nº FINAL de "a" = já respondidos + previstos dos que faltam
            rest = self._dist_restantes(post, p, falta)
            final = np.zeros((n, k + 1))
            for m in range(k + 1):
                final[linhas, np.minimum(n_a + m, k)] += rest[:, m]
            dist_na.append(final)
            p_esc.append(final[:, LIMIAR_DECIDIDO:].sum(axis=1))
            p_th.append(post[:, positivo].sum(axis=1))
            if passo == k:
                break

            # seleção: máxima informação de Fisher no θ estimado (EAP), só itens que faltam
            theta_eap = post @ self.grade
            info = np.where(falta, self._informacao(theta_eap, idx), -np.inf)
            j = info.argmax(axis=1)
            resp = X[linhas, np.asarray(idx)[j]]

            # atualização bayesiana com a resposta dada
            log_post += np.where(resp[:, None] == 1, log_p[:, j].T, log_q[:, j].T)
            falta[linhas, j] = False
            n_a += resp
            ordem[:, passo] = np.asarray(idx)[j] + 1

        return {"p_escore": np.array(p_esc), "p_theta": np.array(p_th),
                "dist_na": np.array(dist_na), "ordem": ordem}

    @staticmethod
    def aplicar_limiar(traj: dict, limiar: float, alvo: str = "escore") -> dict[str, np.ndarray]:
        """Para cada aluno: para no primeiro passo em que um polo atinge o limiar.

        Retorna polo previsto, intensidade prevista e nº de questões (n,).
        """
        prob = traj["p_escore"] if alvo == "escore" else traj["p_theta"]   # (12, n)
        confianca = np.maximum(prob, 1 - prob)
        atingiu = confianca >= limiar
        atingiu[-1] = True                                                   # depois do 11º item, para
        passo = atingiu.argmax(axis=0)                                       # primeiro passo que atingiu
        n = prob.shape[1]
        p_final = prob[passo, np.arange(n)]
        polo = (p_final >= 0.5).astype(np.int8)

        # intensidade: faixa mais provável DENTRO do polo previsto
        dist = traj["dist_na"][passo, np.arange(n)]                          # (n, 12)
        escores_possiveis = 2 * np.arange(ITENS_POR_DIMENSAO + 1) - ITENS_POR_DIMENSAO
        faixa = intensidades(escores_possiveis)
        lado = (escores_possiveis > 0).astype(np.int8)
        prob_faixa = np.stack([(dist * ((faixa == f) & (lado == polo[:, None]))).sum(axis=1)
                               for f in range(3)], axis=1)
        return {"polo": polo, "intensidade": prob_faixa.argmax(axis=1).astype(np.int8), "n_questoes": passo}

    # ------------------------------------------------------------------ máscaras arbitrárias
    def prob_polo_mascara(self, X: np.ndarray, mascara: np.ndarray, d: int) -> np.ndarray:
        """P(polo "a" do ILS completo na dimensão d) para QUALQUER conjunto de itens respondidos.

        Usa só os itens da própria dimensão (o TAC trata as dimensões como
        independentes). Serve de referência para o classificador MLP: é a
        probabilidade "de modelo" calculada pela TRI com os mesmos dados.
        """
        idx = [i - 1 for i in itens_da_dimensao(d)]
        p = self._p_grade(idx)
        resp = X[:, idx].astype(float)
        feito = mascara[:, idx].astype(float)
        log_post = self.log_prior[None, :] + (feito * resp) @ np.log(p).T + (feito * (1 - resp)) @ np.log(1 - p).T
        post = np.exp(log_post - log_post.max(axis=1, keepdims=True))
        post /= post.sum(axis=1, keepdims=True)
        rest = self._dist_restantes(post, p, ~mascara[:, idx])
        n_a = (feito * resp).sum(axis=1).astype(int)
        precisa = np.maximum(LIMIAR_DECIDIDO - n_a, 0)                       # quantos "a" ainda faltam
        acumulada = np.cumsum(rest[:, ::-1], axis=1)[:, ::-1]                # P(restantes >= m)
        return np.where(precisa < acumulada.shape[1],
                        acumulada[np.arange(len(n_a)), np.minimum(precisa, acumulada.shape[1] - 1)], 0.0)

    # ------------------------------------------------------------------ uso na plataforma
    def proxima_questao(self, d: int, respostas: dict[int, int], limiar: float,
                        alvo: str = "escore") -> tuple[int | None, int | None, float]:
        """Um passo do TAC para UM aluno (é o que o backend vai chamar).

        respostas: {item (1..44): 0/1} já dadas nesta dimensão, NA ORDEM em que foram feitas.
        Retorna (próximo item, None, prob) ou (None, polo, prob) se deve parar.
        """
        idx = [i - 1 for i in itens_da_dimensao(d)]
        p = self._p_grade(idx)
        log_post = self.log_prior.copy()
        falta = np.ones(len(idx), dtype=bool)
        n_a = 0
        for item, r in respostas.items():
            j = idx.index(item - 1)
            log_post += np.log(p[:, j]) if r == 1 else np.log(1 - p[:, j])
            falta[j] = False
            n_a += r
        post = np.exp(log_post - log_post.max())
        post /= post.sum()

        if alvo == "escore":
            rest = self._dist_restantes(post[None, :], p, falta[None, :])[0]
            prob = rest[max(LIMIAR_DECIDIDO - n_a, 0):].sum()
        else:
            prob = post[self.grade > 0].sum()
        if max(prob, 1 - prob) >= limiar or not falta.any():
            return None, int(prob >= 0.5), float(prob)
        info = np.where(falta, self._informacao(np.array([post @ self.grade]), idx)[0], -np.inf)
        return idx[int(info.argmax())] + 1, None, float(prob)
