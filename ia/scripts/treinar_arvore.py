"""Etapa 2 — linha de base: questionário adaptativo por árvore de decisão.

Uso (de dentro da pasta ia/):
    python scripts/treinar_arvore.py --config configs/arvore.yaml

O que faz:
  1. Para cada variante e cada profundidade: treina no TREINO e mede na
     VALIDAÇÃO → curva acurácia × nº médio de questões.
  2. Escolhe, só com a validação, a menor profundidade por dimensão que
     atinge a meta (≥ 90%).
  3. Avalia o modelo escolhido UMA vez no TESTE (resultado que vai para o TCC).

Saídas em experimentos/<data>_arvore/:
  curva_validacao.csv, curva_arvore.png, metricas.json,
  arvores_<variante>.txt (árvores legíveis para o apêndice), modelo_<variante>.joblib
"""

import argparse

import joblib
import matplotlib

matplotlib.use("Agg")  # gera imagens sem abrir janela
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

from ils_adaptativo.arvore import QuestionarioArvore
from ils_adaptativo.constantes import DIMENSOES, POLOS
from ils_adaptativo.dados import carregar_conjunto, gabarito, respostas
from ils_adaptativo.metricas import avaliar
from ils_adaptativo import parada_garantida
from ils_adaptativo.registro import Experimento

# Cores e marcadores das variantes (paleta categórica validada para daltonismo;
# marcadores diferentes para continuar legível impresso em preto e branco)
ESTILO = {
    "dimensao": {"cor": "#2a78d6", "marcador": "o", "linha": "-", "rotulo": "só itens da dimensão"},
    "todos": {"cor": "#eb6834", "marcador": "s", "linha": "--", "rotulo": "qualquer um dos 44 itens"},
}


def montar_curva(variante, cfg, X_tr, g_tr, X_val, g_val) -> pd.DataFrame:
    linhas = []
    for p in cfg["profundidades"]:
        modelo = QuestionarioArvore([p] * 4, variante, cfg["criterio"],
                                    cfg["min_amostras_folha"], cfg["seed"])
        modelo.treinar(X_tr, g_tr["polo"], g_tr["intensidade"])
        prev = modelo.prever(X_val)
        for d, nome in enumerate(DIMENSOES):
            linhas.append({
                "variante": variante, "profundidade": p, "dimensao": nome,
                "acuracia_polo": (prev["polo"][:, d] == g_val["polo"][:, d]).mean(),
                "media_questoes": prev["n_questoes"][:, d].mean(),
                "media_questoes_total": prev["n_total"].mean(),
            })
        print(f"  {variante:9s} profundidade {p:2d}: acurácia média "
              f"{(prev['polo'] == g_val['polo']).mean():.4f}, {prev['n_total'].mean():.2f} questões no total")
    return pd.DataFrame(linhas)


def escolher_profundidades(curva: pd.DataFrame, meta: float) -> tuple[list[int], list[bool]]:
    """Menor profundidade que atinge a meta na validação, por dimensão."""
    escolhidas, atingiu = [], []
    for nome in DIMENSOES:
        c = curva[curva["dimensao"] == nome].sort_values("profundidade")
        ok = c[c["acuracia_polo"] >= meta]
        if len(ok):
            escolhidas.append(int(ok["profundidade"].iloc[0]))
            atingiu.append(True)
        else:
            escolhidas.append(int(c["profundidade"].max()))
            atingiu.append(False)
    return escolhidas, atingiu


def grafico(curva: pd.DataFrame, meta: float, referencia: dict, caminho) -> None:
    fig, eixos = plt.subplots(2, 2, figsize=(10, 7.5), sharey=True)
    for eixo, nome in zip(eixos.flat, DIMENSOES):
        for variante, est in ESTILO.items():
            c = curva[(curva["variante"] == variante) & (curva["dimensao"] == nome)]
            if c.empty:
                continue
            # linha tracejada e marcador vazado: se as variantes coincidirem, as duas continuam visíveis
            eixo.plot(c["media_questoes"], c["acuracia_polo"], color=est["cor"], marker=est["marcador"],
                      markersize=7 if variante == "todos" else 4, linewidth=2, linestyle=est["linha"],
                      markerfacecolor="none" if variante == "todos" else est["cor"], label=est["rotulo"])
        q_ref = referencia[nome]
        eixo.plot([q_ref], [1.0], marker="X", markersize=9, color="#1f1f1d", linestyle="none",
                  label="parada garantida (sem IA)")
        eixo.annotate(f"sem IA: {q_ref:.1f}", (q_ref, 1.0), textcoords="offset points", xytext=(-62, -14),
                      fontsize=8, color="#1f1f1d")
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
    eixos[0, 0].legend(loc="lower right", fontsize=9, frameon=False)
    fig.suptitle("Árvore de decisão: acurácia × nº médio de questões (cada ponto = uma profundidade máxima)",
                 fontsize=11)
    fig.tight_layout()
    fig.savefig(caminho, dpi=200)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="configs/arvore.yaml")
    args = parser.parse_args()
    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    treino, val, teste = (carregar_conjunto(n, cfg["diretorio_dados"]) for n in ("treino", "validacao", "teste"))
    X_tr, X_val, X_te = respostas(treino), respostas(val), respostas(teste)
    g_tr, g_val, g_te = gabarito(treino), gabarito(val), gabarito(teste)

    exp = Experimento(cfg["nome_experimento"], cfg)
    print(f"Experimento: {exp.dir}")

    # Referência sem IA (parada garantida), com a ordem dos itens medida no treino
    ordem = parada_garantida.ordem_por_correlacao(X_tr)
    ref = {}
    for nome_conj, X, g in (("validacao", X_val, g_val), ("teste", X_te, g_te)):
        r = parada_garantida.simular(X, ordem)
        ref[nome_conj] = avaliar(g["polo"], r["polo"], r["n_questoes"], g["intensidade"])
    q_ref_val = {k: v["media_questoes"] for k, v in ref["validacao"]["por_dimensao"].items()}
    print(f"Referência sem IA (parada garantida), TESTE: 100% de acerto com "
          f"{ref['teste']['geral']['media_questoes_total']:.2f} questões em média")

    curvas, resumo = [], {"parada_garantida_questoes_teste": ref["teste"]["geral"]["media_questoes_total"]}
    metricas = {"meta_acuracia": cfg["meta_acuracia"], "parada_garantida": ref, "variantes": {}}
    for variante in cfg["variantes"]:
        print(f"\nVariante '{variante}': curva na validação")
        curva = montar_curva(variante, cfg, X_tr, g_tr, X_val, g_val)
        curvas.append(curva)

        prof, atingiu = escolher_profundidades(curva, cfg["meta_acuracia"])
        modelo = QuestionarioArvore(prof, variante, cfg["criterio"], cfg["min_amostras_folha"], cfg["seed"])
        modelo.treinar(X_tr, g_tr["polo"], g_tr["intensidade"])

        resultados = {}
        for nome_conj, X, g in (("validacao", X_val, g_val), ("teste", X_te, g_te)):
            p = modelo.prever(X)
            resultados[nome_conj] = avaliar(g["polo"], p["polo"], p["n_questoes"],
                                            g["intensidade"], p["intensidade"], n_total=p["n_total"])

        metricas["variantes"][variante] = {
            "profundidades_escolhidas": dict(zip(DIMENSOES, prof)),
            "meta_atingida_na_validacao": dict(zip(DIMENSOES, atingiu)),
            **resultados,
        }
        geral = resultados["teste"]["geral"]
        resumo[variante] = {"acc_min_teste": geral["acuracia_polo_minima"],
                            "questoes_teste": geral["media_questoes_total"]}

        with open(exp.caminho(f"arvores_{variante}.txt"), "w", encoding="utf-8") as f:
            f.write(modelo.texto())
        joblib.dump(modelo, exp.caminho(f"modelo_{variante}.joblib"))

        print(f"  profundidades escolhidas: {dict(zip(DIMENSOES, prof))}")
        print(f"  TESTE: acurácia por dimensão "
              f"{ {k: v['acuracia_polo'] for k, v in resultados['teste']['por_dimensao'].items()} }")
        print(f"  TESTE: {geral['media_questoes_total']:.2f} questões em média (de 44); "
              f"todas ≥ 90%: {geral['todas_dimensoes_ge_90']}")

    curva_total = pd.concat(curvas)
    curva_total.round(4).to_csv(exp.caminho("curva_validacao.csv"), index=False)
    grafico(curva_total, cfg["meta_acuracia"], q_ref_val, exp.caminho("curva_arvore.png"))
    exp.finalizar(metricas, resumo=resumo)
    print(f"\nRegistro salvo em {exp.dir}")


if __name__ == "__main__":
    main()
