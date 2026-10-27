"""Abordagem 3, peça (a): classificador MLP de respostas parciais (PyTorch).

O que faz: recebe o estado do questionário (quais itens foram respondidos e
as respostas — ver mascaras.py) e devolve, para as 4 dimensões AO MESMO TEMPO,
a probabilidade de o polo do ILS completo ser o da resposta "a".

Por que um único modelo para as 4 dimensões: assim ele pode usar respostas de
uma dimensão para prever outra (sensorial/intuitivo × sequencial/global são
correlacionados, D9). O TAC, que trata cada dimensão sozinha, não consegue.

Treino:
  - entrada: alunos do TREINO com respostas escondidas por máscaras sorteadas
    de novo A CADA ÉPOCA (o modelo nunca vê o mesmo estado parcial duas vezes,
    o que funciona como aumento de dados);
  - alvo: polo do ILS completo (gabarito) nas 4 dimensões;
  - perda: entropia cruzada binária (BCE), soma das 4 dimensões;
  - parada antecipada: para quando a perda na VALIDAÇÃO (com máscaras fixas)
    não melhora por `paciencia` épocas, e volta para os melhores pesos.

Na política de RL (peça b), é este classificador que dá o resultado quando a
política decide encerrar o questionário.
"""

import numpy as np
import torch
from torch import nn

from .constantes import N_DIMENSOES
from .mascaras import N_ENTRADAS, codificar, sortear_mascaras


class ClassificadorParcial(nn.Module):
    def __init__(self, camadas=(256, 256), dropout: float = 0.0):
        super().__init__()
        blocos, entrada = [], N_ENTRADAS
        for largura in camadas:
            blocos += [nn.Linear(entrada, largura), nn.ReLU()]
            if dropout > 0:
                blocos.append(nn.Dropout(dropout))
            entrada = largura
        blocos.append(nn.Linear(entrada, N_DIMENSOES))  # 4 saídas = 4 logits (um por dimensão)
        self.rede = nn.Sequential(*blocos)
        self.camadas, self.dropout = tuple(camadas), dropout

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.rede(x)  # logits; probabilidade = sigmoide(logit)


def prever_proba(modelo: ClassificadorParcial, X: np.ndarray, mascara: np.ndarray, lote: int = 8192) -> np.ndarray:
    """P(polo "a") nas 4 dimensões: (n, 4)."""
    modelo.eval()
    saidas = []
    with torch.no_grad():
        for i in range(0, len(X), lote):
            entrada = torch.from_numpy(codificar(X[i:i + lote], mascara[i:i + lote]))
            saidas.append(torch.sigmoid(modelo(entrada)).numpy())
    return np.concatenate(saidas)


def treinar(X_tr: np.ndarray, polo_tr: np.ndarray, X_val: np.ndarray, polo_val: np.ndarray,
            cfg: dict, seed: int, log=print) -> tuple[ClassificadorParcial, list[dict]]:
    """Treina o classificador. cfg: camadas, dropout, lr, weight_decay, lote, max_epocas, paciencia."""
    torch.manual_seed(seed)
    rng_treino, rng_val = (np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(2))

    modelo = ClassificadorParcial(cfg["camadas"], cfg["dropout"])
    otimizador = torch.optim.Adam(modelo.parameters(), lr=cfg["lr"], weight_decay=cfg["weight_decay"])
    perda_fn = nn.BCEWithLogitsLoss()

    # Validação com máscaras FIXAS: a perda de uma época é comparável com a da outra
    E_val = torch.from_numpy(codificar(X_val, sortear_mascaras(len(X_val), rng_val)))
    Y_val = torch.from_numpy(polo_val.astype(np.float32))
    Y_tr = torch.from_numpy(polo_tr.astype(np.float32))

    melhor_perda, melhor_estado, sem_melhora, historico = float("inf"), None, 0, []
    for epoca in range(1, cfg["max_epocas"] + 1):
        modelo.train()
        E_tr = torch.from_numpy(codificar(X_tr, sortear_mascaras(len(X_tr), rng_treino)))  # máscaras novas
        ordem = torch.from_numpy(rng_treino.permutation(len(X_tr)))
        soma = 0.0
        for i in range(0, len(ordem), cfg["lote"]):
            lote = ordem[i:i + cfg["lote"]]
            otimizador.zero_grad()
            perda = perda_fn(modelo(E_tr[lote]), Y_tr[lote])
            perda.backward()
            otimizador.step()
            soma += perda.item() * len(lote)

        modelo.eval()
        with torch.no_grad():
            logits = modelo(E_val)
            perda_val = perda_fn(logits, Y_val).item()
            acc_val = ((logits > 0).float() == Y_val).float().mean().item()
        historico.append({"epoca": epoca, "perda_treino": soma / len(ordem),
                          "perda_validacao": perda_val, "acuracia_validacao": acc_val})
        log(f"  época {epoca:3d}: perda treino {soma / len(ordem):.4f} | "
            f"validação {perda_val:.4f} | acurácia validação {acc_val:.4f}")

        if perda_val < melhor_perda - 1e-5:
            melhor_perda, sem_melhora = perda_val, 0
            melhor_estado = {k: v.detach().clone() for k, v in modelo.state_dict().items()}
        else:
            sem_melhora += 1
            if sem_melhora >= cfg["paciencia"]:
                log(f"  parada antecipada: {cfg['paciencia']} épocas sem melhorar")
                break

    modelo.load_state_dict(melhor_estado)
    return modelo, historico


def salvar(modelo: ClassificadorParcial, caminho) -> None:
    torch.save({"camadas": modelo.camadas, "dropout": modelo.dropout, "estado": modelo.state_dict()}, caminho)


def carregar(caminho) -> ClassificadorParcial:
    dados = torch.load(caminho, map_location="cpu")
    modelo = ClassificadorParcial(dados["camadas"], dados["dropout"])
    modelo.load_state_dict(dados["estado"])
    modelo.eval()
    return modelo
