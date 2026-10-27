"""Etapa 3 — TAC clássico com TRI (girth para calibrar, máxima informação de Fisher).

Uso (de dentro da pasta ia/):
    python scripts/treinar_tac.py --config configs/tac.yaml

O que faz:
  1. Estima o 2PL de cada dimensão com girth, só com o TREINO.
  2. Simula o TAC na VALIDAÇÃO para todos os limiares → curva acurácia × nº de questões.
  3. Escolhe o limiar por dimensão (menor que atinge a meta) só com a validação.
  4. Avalia no TESTE: (a) o limiar escolhido e (b) a regra do projeto (95%).

Saídas em experimentos/<data>_tac/:
  itens_girth.csv, curva_validacao.csv, curva_tac.png, metricas.json, modelo_tac.joblib
Leva alguns minutos em CPU (a maior parte é a simulação vetorizada).
"""

import argparse
import time
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

from ils_adaptativo import parada_garantida
from ils_adaptativo.constantes import DIMENSOES, N_DIMENSOES, N_ITENS, POLOS, dimensao_do_item
from ils_adaptativo.dados import carregar_conjunto, gabarito, respostas
from ils_adaptativo.metricas import avaliar
from ils_adaptativo.registro import Experimento
from ils_adaptativo.tac import TAC

ESTILO = {
    "escore": {"cor": "#2a78d6", "marcador": "o", "linha": "-", "rotulo": "TAC, alvo = polo do ILS"},
    "theta": {"cor": "#eb6834", "marcador": "s", "linha": "--", "rotulo": "TAC, alvo = θ > 0"},
}


def simular_conjunto(tac: TAC, X: np.ndarray) -> list[dict]:
    """Trajetória do TAC para as 4 dimensões (uma passada serve para todos os limiares)."""
    trajs = []
    for d in range(N_DIMENSOES):
        t0 = time.time()
        trajs.append(tac.trajetoria(X, d))
        print(f"    {DIMENSOES[d]}: {time.time() - t0:.1f} s")
    return trajs


def resultado(trajs: list[dict], limiares: list[float], alvo: str) -> dict[str, np.ndarray]:
    """Junta as 4 dimensões, cada uma com o seu limiar, em matrizes (n, 4)."""
    partes = [TAC.aplicar_limiar(trajs[d], limiares[d], alvo) for d in range(N_DIMENSOES)]
    return {campo: np.stack([p[campo] for p in partes], axis=1) for campo in ("polo", "intensidade", "n_questoes")}


def ultima_curva_arvore(raiz: Path) -> pd.DataFrame | None:
    candidatos = sorted(raiz.glob("*_arvore/curva_validacao.csv"))
    if not candidatos:
        return None
    c = pd.read_csv(candidatos[-1])
    return c[c["variante"] == "dimensao"]


def grafico(curva, meta, ref_q, arvore, caminho) -> None:
    fig, eixos = plt.subplots(2, 2, figsize=(10, 7.5), sharey=True)
    for eixo, nome in zip(eixos.flat, DIMENSOES):
        if arvore is not None:
            c = arvore[arvore["dimensao"] == nome]
            eixo.plot(c["media_questoes"], c["acuracia_polo"], color="#8c8c86", marker="^", markersize=4,
                      linewidth=1.2, label="árvore de decisão")
        for alvo, est in ESTILO.items():
            c = curva[(curva["alvo"] == alvo) & (curva["dimensao"] == nome)].sort_values("media_questoes")
            if c.empty:
                continue
            eixo.plot(c["media_questoes"], c["acuracia_polo"], color=est["cor"], marker=est["marcador"],
                      markersize=4, linewidth=2, linestyle=est["linha"], label=est["rotulo"])
        eixo.plot([ref_q[nome]], [1.0], marker="X", markersize=9, color="#1f1f1d", linestyle="none",
                  label="parada garantida (sem IA)")
        eixo.axhline(meta, color="#6b6b66", linewidth=1, linestyle="--")
        eixo.text(0.3, meta + 0.004, f"meta {meta:.0%}", color="#3d3d3a", fontsize=8)
        eixo.set_title(f"{POLOS[nome][0]} / {POLOS[nome][1]}", fontsize=11)
        eixo.set_xlim(0, 11.5)
        eixo.set_ylim(0.5, 1.01)
        eixo.grid(color="#e5e4df", linewidth=0.8)
        eixo.spines[["top", "right"]].set_visible(False)
    for eixo in eixos[1]:
        eixo.set_xlabel("nº médio de questões feitas para a dimensão (validação)")
    for eixo in eixos[:, 0]:
        eixo.set_ylabel("acurácia do polo")
    eixos[0, 0].legend(loc="lower right", fontsize=8, frameon=False)
    fig.suptitle("TAC × árvore: acurácia × nº médio de questões (cada ponto do TAC = um limiar de parada)",
                 fontsize=11)
    fig.tight_layout()
    fig.savefig(caminho, dpi=200)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="configs/tac.yaml")
    args = parser.parse_args()
    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    treino, val, teste = (carregar_conjunto(n, cfg["diretorio_dados"]) for n in ("treino", "validacao", "teste"))
    X_tr, X_val, X_te = respostas(treino), respostas(val), respostas(teste)
    g_val, g_te = gabarito(val), gabarito(teste)

    exp = Experimento(cfg["nome_experimento"], cfg)
    print(f"Experimento: {exp.dir}")

    # 1) Calibração com girth (só treino)
    print("Estimando o 2PL com girth (treino)...")
    t0 = time.time()
    tac = TAC(cfg["grade_theta"]["pontos"], cfg["grade_theta"]["maximo"]).ajustar(X_tr)
    print(f"  {time.time() - t0:.1f} s")
    itens = pd.DataFrame({"item": np.arange(1, N_ITENS + 1),
                          "dimensao": [DIMENSOES[dimensao_do_item(i)] for i in range(1, N_ITENS + 1)],
                          "a_girth": tac.a.round(4), "b_girth": tac.b.round(4)})
    gerador = Path(cfg["diretorio_dados"]) / "itens_calibrados.csv"
    if gerador.exists():  # só para DIAGNÓSTICO: o TAC não usa estes valores
        g = pd.read_csv(gerador)
        itens["a_gerador"], itens["b_gerador"] = g["a"].values, g["b"].values
        print(f"  correlação a_girth × a_gerador: {np.corrcoef(itens.a_girth, itens.a_gerador)[0, 1]:.4f}")
    itens.to_csv(exp.caminho("itens_girth.csv"), index=False)

    # Referência sem IA
    ordem = parada_garantida.ordem_por_correlacao(X_tr)
    ref = {}
    for nome_conj, X, g in (("validacao", X_val, g_val), ("teste", X_te, g_te)):
        r = parada_garantida.simular(X, ordem)
        ref[nome_conj] = avaliar(g["polo"], r["polo"], r["n_questoes"], g["intensidade"])

    # 2) Curva na validação
    print("Simulando o TAC na validação...")
    traj_val = simular_conjunto(tac, X_val)
    linhas = []
    for alvo in cfg["alvos"]:
        for lim in cfg["limiares"]:
            for d, nome in enumerate(DIMENSOES):
                r = TAC.aplicar_limiar(traj_val[d], lim, alvo)
                linhas.append({"alvo": alvo, "limiar": lim, "dimensao": nome,
                               "acuracia_polo": (r["polo"] == g_val["polo"][:, d]).mean(),
                               "media_questoes": r["n_questoes"].mean()})
    curva = pd.DataFrame(linhas)
    curva.round(4).to_csv(exp.caminho("curva_validacao.csv"), index=False)

    # 3) Escolha do limiar por dimensão (só validação)
    escolhidos = {}
    for alvo in cfg["alvos"]:
        lims, atingiu = [], []
        for nome in DIMENSOES:
            c = curva[(curva["alvo"] == alvo) & (curva["dimensao"] == nome)].sort_values("limiar")
            ok = c[c["acuracia_polo"] >= cfg["meta_acuracia"]]
            lims.append(float(ok["limiar"].iloc[0]) if len(ok) else float(c["limiar"].max()))
            atingiu.append(bool(len(ok)))
        escolhidos[alvo] = (lims, atingiu)

    # 4) Teste
    print("Simulando o TAC no teste...")
    traj_te = simular_conjunto(tac, X_te)
    metricas = {"meta_acuracia": cfg["meta_acuracia"], "parada_garantida": ref, "alvos": {}}
    resumo = {"parada_garantida_questoes_teste": ref["teste"]["geral"]["media_questoes_total"]}
    print(f"\nReferência sem IA (parada garantida), TESTE: 100% com "
          f"{ref['teste']['geral']['media_questoes_total']:.2f} questões")
    for alvo in cfg["alvos"]:
        lims, atingiu = escolhidos[alvo]
        bloco = {"limiares_escolhidos": dict(zip(DIMENSOES, lims)),
                 "meta_atingida_na_validacao": dict(zip(DIMENSOES, atingiu))}
        for rotulo, lista in (("limiar_escolhido", lims), ("limiar_projeto", [cfg["limiar_projeto"]] * 4)):
            for nome_conj, trajs, g in (("validacao", traj_val, g_val), ("teste", traj_te, g_te)):
                r = resultado(trajs, lista, alvo)
                bloco.setdefault(rotulo, {})[nome_conj] = avaliar(
                    g["polo"], r["polo"], r["n_questoes"], g["intensidade"], r["intensidade"])
            geral = bloco[rotulo]["teste"]["geral"]
            acc = {k: v["acuracia_polo"] for k, v in bloco[rotulo]["teste"]["por_dimensao"].items()}
            print(f"[alvo={alvo}] {rotulo} {dict(zip(DIMENSOES, lista))}")
            print(f"    TESTE: acurácia {acc}")
            print(f"    TESTE: {geral['media_questoes_total']:.2f} questões em média; "
                  f"todas ≥ 90%: {geral['todas_dimensoes_ge_90']}")
            resumo[f"{alvo}_{rotulo}"] = {"acc_min": geral["acuracia_polo_minima"],
                                          "questoes": geral["media_questoes_total"]}
        metricas["alvos"][alvo] = bloco

    arvore = ultima_curva_arvore(exp.raiz) if cfg.get("comparar_com_arvore") else None
    ref_q = {k: v["media_questoes"] for k, v in ref["validacao"]["por_dimensao"].items()}
    grafico(curva, cfg["meta_acuracia"], ref_q, arvore, exp.caminho("curva_tac.png"))
    joblib.dump(tac, exp.caminho("modelo_tac.joblib"))
    exp.finalizar(metricas, resumo=resumo)
    print(f"\nRegistro salvo em {exp.dir}")


if __name__ == "__main__":
    main()
