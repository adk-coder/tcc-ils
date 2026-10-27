"""Etapa 4a — treina e avalia o classificador MLP de respostas parciais.

Uso (de dentro da pasta ia/):
    python scripts/treinar_classificador.py --config configs/classificador.yaml

Perguntas que este experimento responde (todas na VALIDAÇÃO):
  1. O MLP prevê o polo tão bem quanto o modelo de TRI (TAC) com as mesmas
     respostas? (se sim, ele aprendeu o essencial sem conhecer a TRI)
  2. As probabilidades dele são confiáveis (calibradas)? A política de RL vai
     depender delas.
  3. Saber as respostas das OUTRAS dimensões ajuda? (correlação D9)

Saídas em experimentos/<data>_classificador/:
  classificador.pt, historico_treino.csv, curva_k_itens.csv,
  curva_classificador.png, metricas.json
"""

import argparse
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

from ils_adaptativo import classificador as clf
from ils_adaptativo.avaliacao_parcial import curva_k_itens, prob_tac, resumo_por_dimensao
from ils_adaptativo.constantes import DIMENSOES, POLOS
from ils_adaptativo.dados import carregar_conjunto, gabarito, respostas
from ils_adaptativo.mascaras import sortear_mascaras
from ils_adaptativo.registro import Experimento
from ils_adaptativo.tac import TAC

ESTILO = {
    "MLP, só a dimensão": {"cor": "#2a78d6", "marcador": "o", "linha": "-"},
    "MLP, com as outras 3 dimensões": {"cor": "#eb6834", "marcador": "s", "linha": "--"},
    "TRI (modelo do TAC)": {"cor": "#8c8c86", "marcador": "^", "linha": ":"},
}


def grafico(curva: pd.DataFrame, caminho) -> None:
    fig, eixos = plt.subplots(2, 2, figsize=(10, 7.5), sharey=True)
    for eixo, nome in zip(eixos.flat, DIMENSOES):
        for rotulo, est in ESTILO.items():
            c = curva[(curva["modelo"] == rotulo) & (curva["dimensao"] == nome)]
            eixo.plot(c["k"], c["acuracia"], color=est["cor"], marker=est["marcador"], markersize=4,
                      linewidth=2, linestyle=est["linha"], label=rotulo)
        eixo.axhline(0.9, color="#6b6b66", linewidth=1, linestyle="--")
        eixo.set_title(f"{POLOS[nome][0]} / {POLOS[nome][1]}", fontsize=11)
        eixo.set_xticks(range(0, 12))
        eixo.set_ylim(0.45, 1.01)
        eixo.grid(color="#e5e4df", linewidth=0.8)
        eixo.spines[["top", "right"]].set_visible(False)
    for eixo in eixos[1]:
        eixo.set_xlabel("nº de itens respondidos DA PRÓPRIA dimensão")
    for eixo in eixos[:, 0]:
        eixo.set_ylabel("acurácia do polo (validação)")
    eixos[0, 0].legend(loc="lower right", fontsize=8, frameon=False)
    fig.suptitle("Classificador de respostas parciais: acurácia × itens conhecidos", fontsize=11)
    fig.tight_layout()
    fig.savefig(caminho, dpi=200)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="configs/classificador.yaml")
    args = parser.parse_args()
    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    treino, val = (carregar_conjunto(n, cfg["diretorio_dados"]) for n in ("treino", "validacao"))
    X_tr, X_val = respostas(treino), respostas(val)
    polo_tr, polo_val = gabarito(treino)["polo"], gabarito(val)["polo"]

    exp = Experimento(cfg["nome_experimento"], cfg)
    print(f"Experimento: {exp.dir}")

    print("Treinando o MLP...")
    t0 = time.time()
    modelo, historico = clf.treinar(X_tr, polo_tr, X_val, polo_val, cfg["rede"], cfg["seed"])
    tempo_treino = time.time() - t0
    print(f"  {tempo_treino:.1f} s")
    clf.salvar(modelo, exp.caminho("classificador.pt"))
    pd.DataFrame(historico).round(5).to_csv(exp.caminho("historico_treino.csv"), index=False)

    print("Estimando o 2PL com girth para a referência de TRI...")
    tac = TAC().ajustar(X_tr)
    fn_mlp = lambda X, m: clf.prever_proba(modelo, X, m)  # noqa: E731
    fn_tac = prob_tac(tac)

    # 1 e 2) Máscaras aleatórias (mesmo sorteio para os dois modelos)
    print("Avaliando com máscaras aleatórias...")
    mascara = sortear_mascaras(len(X_val), np.random.default_rng([cfg["seed"], 99]))
    aleatorias = {"mlp": resumo_por_dimensao(fn_mlp(X_val, mascara), polo_val),
                  "tri": resumo_por_dimensao(fn_tac(X_val, mascara), polo_val)}
    for d in DIMENSOES:
        m, t = aleatorias["mlp"][d], aleatorias["tri"][d]
        print(f"  {d}: acurácia MLP {m['acuracia']:.4f} × TRI {t['acuracia']:.4f} | "
              f"ECE MLP {m['ece']:.4f} × TRI {t['ece']:.4f}")

    # 3) Curva por nº de itens conhecidos da própria dimensão
    print("Curva por nº de itens conhecidos...")
    curva = pd.DataFrame(curva_k_itens({
        "MLP, só a dimensão": (fn_mlp, "nenhuma"),
        "MLP, com as outras 3 dimensões": (fn_mlp, "todas"),
        "TRI (modelo do TAC)": (fn_tac, "nenhuma"),
    }, X_val, polo_val, cfg["seed"]))
    curva.round(4).to_csv(exp.caminho("curva_k_itens.csv"), index=False)
    grafico(curva, exp.caminho("curva_classificador.png"))

    # ganho das outras dimensões com 0 e 3 itens da própria
    ganho = {}
    for d in DIMENSOES:
        c = curva[curva["dimensao"] == d].pivot(index="k", columns="modelo", values="acuracia")
        ganho[d] = {f"k={k}": round(float(c.loc[k, "MLP, com as outras 3 dimensões"]
                                          - c.loc[k, "MLP, só a dimensão"]), 4) for k in (0, 3)}
    print("  ganho de acurácia por conhecer as outras dimensões:", ganho)

    exp.finalizar({"tempo_treino_s": round(tempo_treino, 1), "epocas": len(historico),
                   "mascaras_aleatorias": aleatorias, "ganho_outras_dimensoes": ganho},
                  resumo={"acc_mlp": {d: v["acuracia"] for d, v in aleatorias["mlp"].items()},
                          "acc_tri": {d: v["acuracia"] for d, v in aleatorias["tri"].items()}})
    print(f"\nRegistro salvo em {exp.dir}")


if __name__ == "__main__":
    main()
