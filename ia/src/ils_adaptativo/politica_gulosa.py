"""Linha de base SEM RL para a abordagem 3: política gulosa com o classificador.

Usa o MESMO ambiente e o MESMO classificador da política de RL, mas com uma
regra fixa escrita à mão:
  1. se todas as dimensões têm confiança >= limiar, ENCERRA;
  2. senão, escolhe a dimensão com MENOR confiança e pergunta o item ainda não
     feito dela com maior correlação item-resto (medida no treino).

Por que existe: separa o que vem do classificador do que vem do RL. Se o RL
não superar esta regra simples, o ganho do sistema não está no aprendizado
por reforço, e isso precisa ser dito no texto.
"""

import numpy as np

from .ambiente import ACAO_ENCERRAR, DIMENSAO_DO_INDICE
from .calibracao import correlacoes_itens
from .constantes import N_ITENS
from .mascaras import N_ENTRADAS


def criar(X_treino: np.ndarray, limiar: float):
    """Devolve politica(obs, mascaras) -> acoes, no formato de ambiente.jogar_lote."""
    r = correlacoes_itens(X_treino, "item_resto")

    def politica(obs: np.ndarray, mascaras: np.ndarray) -> np.ndarray:
        confianca = (np.abs(obs[:, N_ENTRADAS:]) + 1) / 2           # obs guarda 2p−1 → max(p, 1−p)
        falta = confianca < limiar                                   # (n, 4) dimensões ainda incertas
        conf_item = confianca[:, DIMENSAO_DO_INDICE]                 # (n, 44) confiança da dimensão de cada item
        permitido = mascaras[:, :N_ITENS] & falta[:, DIMENSAO_DO_INDICE]
        # prioridade: dimensão menos confiante primeiro; dentro dela, item mais discriminativo
        prioridade = np.where(permitido, -100 * conf_item + r[None, :], -np.inf)
        acoes = prioridade.argmax(axis=1)
        acoes[~np.isfinite(prioridade.max(axis=1))] = ACAO_ENCERRAR
        return acoes

    return politica
