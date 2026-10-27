"""Abordagem 3, peça (b): o "jogo" do questionário, em numpy puro.

Esta é a lógica do ambiente de RL, separada do Gymnasium para poder ser
testada sozinha e para avaliar muitos alunos de uma vez (lote).

O JOGO (um episódio = um aluno):
  - Estado (observação, 92 números):
      88 = mesmo formato da entrada do classificador (o que já foi perguntado
           e as respostas, ver mascaras.py)
       4 = confiança atual do classificador em cada dimensão, como 2p − 1
           (dá à política uma noção de "o quanto já sei" sem ela ter que
           reaprender o que o classificador já sabe)
  - Ações (45): perguntar um dos 44 itens, ou 44 = ENCERRAR.
      Máscara de ações: itens já perguntados ficam proibidos; encerrar é sempre
      permitido. Quando os 44 forem perguntados, o episódio acaba sozinho.
  - Recompensa:
      −λ a cada pergunta feita;
      ao encerrar, +1 por dimensão em que o classificador acerta o polo (0 a 4).
    Com γ = 1 (sem desconto), o retorno do episódio é
        (nº de dimensões corretas) − λ · (nº de perguntas),
    então λ é literalmente "quanto uma pergunta a mais custa em acertos".
    Opção recompensa = "probabilidade": em vez de 0/1 por dimensão, usa a
    probabilidade que o classificador deu ao polo correto (mesma média, menos
    variância; útil se o treino com 0/1 ficar instável).
    Opção recompensa = "potencial" (PADRÃO, ver D17): recompensa a cada pergunta
        Φ(depois) − Φ(antes) − λ,   com Φ = Σ_d P(polo correto da dimensão d)
    e 0 ao encerrar. Somando o episódio, os termos se cancelam ("telescopam"):
        retorno = Φ(final) − Φ(início) − λ · (nº de perguntas),
    e Φ(início) é igual para todos. Ou seja, o MESMO objetivo da opção
    "probabilidade", mas a política recebe o sinal na hora em que a pergunta
    ajudou (ou não), em vez de só no fim. É a "modelagem de recompensa baseada
    em potencial" (Ng, Harada e Russell, 1999), que não muda a política ótima.

Quem dá a resposta final é sempre o CLASSIFICADOR (peça a); a política só
decide o que perguntar e quando parar.
"""

import numpy as np

from .constantes import N_DIMENSOES, N_ITENS, dimensao_do_item
from .mascaras import N_ENTRADAS, codificar

N_ACOES = N_ITENS + 1
ACAO_ENCERRAR = N_ITENS
N_OBSERVACAO = N_ENTRADAS + N_DIMENSOES
DIMENSAO_DO_INDICE = np.array([dimensao_do_item(i + 1) for i in range(N_ITENS)])


class ClassificadorNumpy:
    """O MLP da peça (a) rodando em numpy (mesmos pesos, sem PyTorch).

    Dentro do ambiente o classificador é chamado a cada passo; em numpy isso é
    mais rápido para 1 aluno e permite testar o ambiente sem PyTorch.
    """

    def __init__(self, pesos: list[tuple[np.ndarray, np.ndarray]]):
        self.pesos = [(np.asarray(W, np.float32), np.asarray(b, np.float32)) for W, b in pesos]

    @classmethod
    def de_torch(cls, modelo) -> "ClassificadorNumpy":
        from torch import nn
        return cls([(c.weight.detach().cpu().numpy(), c.bias.detach().cpu().numpy())
                    for c in modelo.rede if isinstance(c, nn.Linear)])

    def prob(self, entrada: np.ndarray) -> np.ndarray:
        h = entrada.astype(np.float32)
        for i, (W, b) in enumerate(self.pesos):
            h = h @ W.T + b
            if i < len(self.pesos) - 1:
                h = np.maximum(h, 0.0)  # ReLU nas camadas ocultas
        return 1.0 / (1.0 + np.exp(-h))


class QuestionarioLote:
    """Vários alunos jogando ao mesmo tempo (cada um no seu ritmo)."""

    def __init__(self, X: np.ndarray, polo: np.ndarray, classificador: ClassificadorNumpy,
                 lam: float, recompensa: str = "acerto"):
        if recompensa not in ("acerto", "probabilidade", "potencial"):
            raise ValueError("recompensa deve ser 'acerto', 'probabilidade' ou 'potencial'")
        self.X, self.polo, self.clf = X, polo, classificador
        self.lam, self.tipo_recompensa = lam, recompensa
        n = len(X)
        self.perguntado = np.zeros((n, N_ITENS), dtype=bool)
        self.encerrado = np.zeros(n, dtype=bool)
        self._prob = self.clf.prob(codificar(self.X, self.perguntado))

    def observacao(self) -> np.ndarray:
        return np.concatenate([codificar(self.X, self.perguntado), 2 * self._prob - 1], axis=1).astype(np.float32)

    def mascara_acoes(self) -> np.ndarray:
        """(n, 45): True = ação permitida."""
        return np.concatenate([~self.perguntado, np.ones((len(self.X), 1), dtype=bool)], axis=1)

    def _potencial(self, linhas: np.ndarray) -> np.ndarray:
        """Φ = soma, nas 4 dimensões, da probabilidade dada ao polo CORRETO."""
        p, real = self._prob[linhas], self.polo[linhas]
        return np.where(real == 1, p, 1 - p).sum(axis=1)

    def _recompensa_final(self, linhas: np.ndarray) -> np.ndarray:
        p, real = self._prob[linhas], self.polo[linhas]
        if self.tipo_recompensa == "potencial":
            return np.zeros(len(linhas))       # todo o sinal já veio pergunta a pergunta
        if self.tipo_recompensa == "acerto":
            return ((p >= 0.5) == (real == 1)).sum(axis=1).astype(float)
        return np.where(real == 1, p, 1 - p).sum(axis=1)

    def passo(self, acoes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Aplica uma ação por aluno ativo. Retorna (recompensa (n,), acabou_agora (n,))."""
        acoes = np.asarray(acoes)
        n = len(self.X)
        recompensa = np.zeros(n)
        acabou = np.zeros(n, dtype=bool)
        ativos = ~self.encerrado

        # perguntas
        perg = ativos & (acoes != ACAO_ENCERRAR)
        if perg.any():
            linhas = np.where(perg)[0]
            if self.perguntado[linhas, acoes[linhas]].any():
                raise ValueError("ação inválida: item já perguntado (a máscara de ações foi ignorada)")
            antes = self._potencial(linhas)
            self.perguntado[linhas, acoes[linhas]] = True
            recompensa[linhas] -= self.lam
            self._prob[linhas] = self.clf.prob(codificar(self.X[linhas], self.perguntado[linhas]))
            if self.tipo_recompensa == "potencial":
                recompensa[linhas] += self._potencial(linhas) - antes

        # encerrar (por escolha, ou porque não há mais itens)
        fim = ativos & ((acoes == ACAO_ENCERRAR) | self.perguntado.all(axis=1))
        if fim.any():
            linhas = np.where(fim)[0]
            recompensa[linhas] += self._recompensa_final(linhas)
            self.encerrado[linhas] = True
            acabou[linhas] = True
        return recompensa, acabou

    def resultado(self) -> dict[str, np.ndarray]:
        """Polo previsto (n, 4), nº de questões por dimensão (n, 4) e total (n,)."""
        n_q = np.stack([self.perguntado[:, DIMENSAO_DO_INDICE == d].sum(axis=1)
                        for d in range(N_DIMENSOES)], axis=1)
        return {"polo": (self._prob >= 0.5).astype(np.int8), "prob": self._prob.copy(),
                "n_questoes": n_q, "n_total": self.perguntado.sum(axis=1)}


def jogar_lote(X: np.ndarray, polo: np.ndarray, classificador: ClassificadorNumpy, politica,
               lam: float = 0.0) -> dict[str, np.ndarray]:
    """Joga o questionário com TODOS os alunos de X até o fim.

    politica(observacoes (m, 92), mascaras (m, 45)) -> acoes (m,)
    É assim que a política treinada é avaliada (muito mais rápido que 1 a 1).
    """
    jogo = QuestionarioLote(X, polo, classificador, lam)
    while not jogo.encerrado.all():
        ativos = np.where(~jogo.encerrado)[0]
        acoes = np.full(len(X), ACAO_ENCERRAR)
        acoes[ativos] = politica(jogo.observacao()[ativos], jogo.mascara_acoes()[ativos])
        jogo.passo(acoes)
    return jogo.resultado()
