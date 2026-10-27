"""Abordagem 3, peça (b): o ambiente no formato do Gymnasium (para o MaskablePPO).

É só uma "casca" em volta de `QuestionarioLote` (ambiente.py) com 1 aluno:
a cada episódio sorteia um aluno do TREINO e joga o questionário com ele.

O MaskablePPO (sb3-contrib) procura um método `action_masks()` no ambiente
para saber quais ações são permitidas em cada estado.
"""

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from .ambiente import N_ACOES, N_OBSERVACAO, ClassificadorNumpy, QuestionarioLote


class AmbienteILS(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, X: np.ndarray, polo: np.ndarray, classificador: ClassificadorNumpy,
                 lam: float, recompensa: str = "acerto"):
        super().__init__()
        self.X, self.polo, self.clf = X, polo, classificador
        self.lam, self.recompensa = lam, recompensa
        self.observation_space = spaces.Box(low=-1.0, high=1.0, shape=(N_OBSERVACAO,), dtype=np.float32)
        self.action_space = spaces.Discrete(N_ACOES)
        self._jogo = None

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)  # cria self.np_random com a seed (reprodutibilidade)
        aluno = int(self.np_random.integers(len(self.X)))
        self._jogo = QuestionarioLote(self.X[aluno:aluno + 1], self.polo[aluno:aluno + 1],
                                      self.clf, self.lam, self.recompensa)
        return self._jogo.observacao()[0], {}

    def step(self, action):
        recompensa, acabou = self._jogo.passo(np.array([int(action)]))
        info = {}
        if acabou[0]:  # informações do episódio, úteis para acompanhar o treino
            r = self._jogo.resultado()
            info = {"n_questoes": int(r["n_total"][0]),
                    "acertos": int((r["polo"][0] == self._jogo.polo[0]).sum())}
        return self._jogo.observacao()[0], float(recompensa[0]), bool(acabou[0]), False, info

    def action_masks(self) -> np.ndarray:
        return self._jogo.mascara_acoes()[0]
