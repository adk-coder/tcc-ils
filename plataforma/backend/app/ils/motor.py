"""Motor do questionário adaptativo do ILS usado pela plataforma.

É uma cópia enxuta, só com numpy, de TAC.proxima_questao (ia/src/ils_adaptativo/tac.py),
com o alvo "escore": a abordagem escolhida nos experimentos (D14 de docs/decisoes.md).
O teste ia/testes/test_motor_plataforma.py confere que este arquivo toma EXATAMENTE as
mesmas decisões que o TAC avaliado nos experimentos.

Por que copiar em vez de importar o pacote ia/? O backend não deve depender do ambiente
de pesquisa (girth, torch, pandas...). Ele só precisa dos números do modelo: a, b de cada
item e o limiar de parada de cada dimensão, gravados em modelo_tac.json pelo script
ia/scripts/exportar_modelo.py.

Como uma pergunta é escolhida (resumo para a banca):
  1. As 4 dimensões são independentes. Para cada uma, a posteriori de θ numa grade
     (prior Normal(0,1)) é atualizada com as respostas já dadas naquela dimensão.
  2. Calcula-se P(polo do ILS completo = "a"), somando as respostas já dadas com a
     distribuição prevista das que faltam. Se max(P, 1−P) >= limiar da dimensão, ou se
     os 11 itens já foram feitos, a dimensão está decidida.
  3. Entre as dimensões ainda não decididas, pergunta-se na que tem MENOS respostas
     (rodízio), o item de máxima informação de Fisher no θ estimado.
  Como as dimensões não se influenciam, o rodízio não muda o resultado de nenhuma
  delas: cada uma termina exatamente como na simulação dos experimentos.
"""

import json
from pathlib import Path

import numpy as np

N_ITENS = 44
N_DIMENSOES = 4
ITENS_POR_DIMENSAO = 11
LIMIAR_DECIDIDO = ITENS_POR_DIMENSAO // 2 + 1        # 6 respostas iguais decidem o polo

DIMENSOES = ["ati_ref", "sen_int", "vis_ver", "seq_glo"]
# (polo da resposta "a", polo da resposta "b")
POLOS = {"ati_ref": ("ativo", "reflexivo"), "sen_int": ("sensorial", "intuitivo"),
         "vis_ver": ("visual", "verbal"), "seq_glo": ("sequencial", "global")}

CAMINHO_MODELO = Path(__file__).with_name("modelo_tac.json")


def dimensao_do_item(item: int) -> int:
    return (item - 1) % N_DIMENSOES


def itens_da_dimensao(d: int) -> list[int]:
    return [i for i in range(1, N_ITENS + 1) if dimensao_do_item(i) == d]


class MotorILS:
    def __init__(self, a, b, limiares, n_grade: int = 61, theta_max: float = 4.0, info: dict | None = None):
        self.a = np.asarray(a, dtype=float)
        self.b = np.asarray(b, dtype=float)
        if self.a.shape != (N_ITENS,) or self.b.shape != (N_ITENS,) or len(limiares) != N_DIMENSOES:
            raise ValueError("modelo inválido: são precisos 44 valores de a e de b e 4 limiares")
        self.limiares = [float(x) for x in limiares]
        self.grade = np.linspace(-theta_max, theta_max, n_grade)
        prior = np.exp(-0.5 * self.grade**2)
        self.log_prior = np.log(prior / prior.sum())
        self.info = info or {}          # de onde veio o modelo (experimento, desempenho no teste)

    @classmethod
    def de_arquivo(cls, caminho: Path | None = None) -> "MotorILS":
        m = json.loads(Path(caminho or CAMINHO_MODELO).read_text(encoding="utf-8"))
        return cls(m["a"], m["b"], [m["limiares"][nome] for nome in DIMENSOES],
                   m["grade"]["pontos"], m["grade"]["maximo"], info=m)

    # ------------------------------------------------------------------ uma dimensão
    def avaliar_dimensao(self, d: int, respostas: dict[int, int]) -> tuple[int | None, int | None, float]:
        """Mesmo algoritmo de TAC.proxima_questao (alvo "escore").

        respostas: {item (1..44): 1 = "a", 0 = "b"} já dadas NESTA dimensão.
        Retorna (próximo item, None, P(polo "a")) ou (None, polo, P(polo "a")) se decidiu.
        """
        idx = [i - 1 for i in itens_da_dimensao(d)]
        p = 1.0 / (1.0 + np.exp(-self.a[idx][None, :] * (self.grade[:, None] - self.b[idx][None, :])))  # (G, 11)

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

        # nº de respostas "a" que ainda virão: Poisson-binomial para cada θ, integrada no posterior
        dist = np.zeros((len(self.grade), ITENS_POR_DIMENSAO + 1))
        dist[:, 0] = 1.0
        for j in range(len(idx)):
            pj = p[:, j] * falta[j]                     # item já feito → não soma (prob. 0)
            novo = dist * (1 - pj)[:, None]
            novo[:, 1:] += dist[:, :-1] * pj[:, None]
            dist = novo
        restantes = post @ dist
        prob = float(restantes[max(LIMIAR_DECIDIDO - n_a, 0):].sum())

        if max(prob, 1 - prob) >= self.limiares[d] or not falta.any():
            return None, int(prob >= 0.5), prob

        # máxima informação de Fisher a²·P·(1−P) no θ estimado (EAP), só itens que faltam
        theta = post @ self.grade
        pt = 1.0 / (1.0 + np.exp(-self.a[idx] * (theta - self.b[idx])))
        info = np.where(falta, self.a[idx] ** 2 * pt * (1 - pt), -np.inf)
        return idx[int(info.argmax())] + 1, None, prob

    # ------------------------------------------------------------------ questionário inteiro
    def proxima(self, respostas: list[tuple[int, int]]) -> dict:
        """respostas: [(item, 1/0), ...] na ordem em que foram dadas.

        Retorna {"item": próximo item ou None (acabou), "dimensoes": [estado de cada dimensão]}.
        """
        por_dimensao: list[dict[int, int]] = [{} for _ in range(N_DIMENSOES)]
        for item, r in respostas:
            por_dimensao[dimensao_do_item(item)][int(item)] = int(r)

        dimensoes = []
        for d, nome in enumerate(DIMENSOES):
            proximo, polo, prob = self.avaliar_dimensao(d, por_dimensao[d])
            dimensoes.append({"dimensao": nome, "proximo": proximo, "polo": polo, "prob": prob,
                              "n_questoes": len(por_dimensao[d])})

        pendentes = [x for x in dimensoes if x["proximo"] is not None]
        # rodízio: a dimensão pendente com menos respostas (empate → a primeira)
        item = min(pendentes, key=lambda x: x["n_questoes"])["proximo"] if pendentes else None
        return {"item": item, "dimensoes": dimensoes}
