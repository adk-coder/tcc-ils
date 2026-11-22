"""Análise final do TAC escolhido (D19 / D20): métricas completas no conjunto de TESTE.

Uso (de dentro da pasta ia/):
    python scripts/analisar_resultados.py [--experimento experimentos/2026-10-25_092249_tac]
                                          [--dados dados/sintetico]
                                          [--alvo escore]
                                          [--experimento-arvore experimentos/2026-10-25_085918_arvore]
                                          [--experimento-rl experimentos/2026-10-29_125924_rl]

O que faz:
  1. Lê o modelo TAC e os limiares escolhidos na validação do experimento indicado.
  2. Re-simula o TAC no TESTE com esses limiares.
  3. Calcula métricas que não estavam no metricas.json do treino:
     - IC de 95% (Wilson) da acurácia de cada dimensão;
     - acurácia do PERFIL COMPLETO (4 dimensões certas de uma vez);
     - distribuição de erros por aluno (0 a 4 dimensões erradas);
     - distribuição completa do nº de questões (mediana, p10, p90, mín, máx).
  4. Calcula a acurácia por polo (balanceada) para o TAC e para a árvore de decisão.
  5. Gera questoes_por_aluno.png, acerto_por_intensidade.png e versões TCC das
     três curvas (sem título interno, vírgula decimal nos eixos).
  6. Salva analise.json, acuracia_por_polo.csv e cria entrada no registro de experimentos.
  7. Para se qualquer número divergir dos valores já registrados no dossiê.

NÃO altera o modelo nem os limiares escolhidos na validação (D14/D19).
"""

import argparse
import json
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd
import yaml

from ils_adaptativo.arvore import QuestionarioArvore  # noqa: F401 — necessário para joblib.load
from ils_adaptativo.constantes import DIMENSOES, POLOS
from ils_adaptativo.dados import carregar_conjunto, gabarito, respostas
from ils_adaptativo.escore import NOMES_INTENSIDADE
from ils_adaptativo.registro import Experimento
from ils_adaptativo.tac import TAC


def wilson_ic95(acertos: int, n: int) -> tuple[float, float]:
    """IC de 95% de Wilson para uma proporção (correto mesmo com p perto de 0 ou 1)."""
    z = 1.96
    p = acertos / n
    centro = (p + z**2 / (2 * n)) / (1 + z**2 / n)
    margem = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / (1 + z**2 / n)
    return round(float(centro - margem), 4), round(float(centro + margem), 4)


def acuracia_por_polo(
    polo_real: np.ndarray,
    polo_prev: np.ndarray,
    polo_a: str,
    polo_b: str,
) -> dict:
    """n, %, acurácia dentro do polo e Wilson IC95% para cada polo + acurácia balanceada.

    Convenção: polo_val=1 → polo_a ("resposta a"), polo_val=0 → polo_b ("resposta b").
    """
    n = len(polo_real)
    resultado: dict = {}
    accs: list[float] = []
    for polo_val, polo_nome in ((1, polo_a), (0, polo_b)):
        mask = polo_real == polo_val
        n_polo = int(mask.sum())
        pct = round(100.0 * n_polo / n, 1)
        if n_polo == 0:
            resultado[polo_nome] = {
                "n": 0, "percentual": 0.0,
                "acuracia": None, "ic95_low": None, "ic95_high": None,
            }
            continue
        acertos = int((polo_prev[mask] == polo_val).sum())
        acc = round(acertos / n_polo, 4)
        ic_low, ic_high = wilson_ic95(acertos, n_polo)
        resultado[polo_nome] = {
            "n": n_polo, "percentual": pct, "acuracia": acc,
            "ic95_low": ic_low, "ic95_high": ic_high,
        }
        accs.append(acc)
    resultado["acuracia_balanceada"] = round(sum(accs) / len(accs), 4) if len(accs) == 2 else None
    return resultado


def _imprimir_polo_tabela(nome_modelo: str, polo_stats: dict) -> None:
    print(f"\n{'=' * 72}")
    print(f"ACURÁCIA POR POLO — {nome_modelo}")
    print(f"{'=' * 72}")
    print(f"  {'Dimensão':<10}  {'Polo':<12}  {'n':>7}  {'%':>5}  "
          f"{'Acurácia':>10}  {'IC 95% Wilson':>24}  {'Bal.':>8}")
    print(f"  {'-' * 72}")
    for nome in DIMENSOES:
        stats = polo_stats[nome]
        polo_a_nome, polo_b_nome = POLOS[nome]
        bal = stats.get("acuracia_balanceada")
        for i, polo_nome in enumerate((polo_a_nome, polo_b_nome)):
            v = stats[polo_nome]
            if v["acuracia"] is None:
                ic_str, acc_str = "—", "—"
            else:
                ic_str = f"[{v['ic95_low']:.4f}, {v['ic95_high']:.4f}]"
                acc_str = f"{v['acuracia']:.4f}"
            bal_str = f"{bal:.4f}" if (i == 0 and bal is not None) else ""
            dim_str = nome if i == 0 else ""
            print(f"  {dim_str:<10}  {polo_nome:<12}  {v['n']:>7}  {v['percentual']:>4.1f}%  "
                  f"{acc_str:>10}  {ic_str:>24}  {bal_str:>8}")


# ---------------------------------------------------------------------------
# Estilos visuais das variantes (replicados dos scripts de treino para as figuras TCC)
_ESTILO_ARVORE = {
    "dimensao": {"cor": "#2a78d6", "marcador": "o", "linha": "-",  "rotulo": "só itens da dimensão"},
    "todos":    {"cor": "#eb6834", "marcador": "s", "linha": "--", "rotulo": "qualquer um dos 44 itens"},
}
_ESTILO_TAC = {
    "escore": {"cor": "#2a78d6", "marcador": "o", "linha": "-",  "rotulo": "TAC, alvo = polo do ILS"},
    "theta":  {"cor": "#eb6834", "marcador": "s", "linha": "--", "rotulo": "TAC, alvo = θ > 0"},
}


def figura_arvore_tcc(exp_arvore: Path, caminho) -> None:
    """Versão da curva da árvore para o TCC: sem título de figura, vírgula decimal no eixo y."""
    curva = pd.read_csv(exp_arvore / "curva_validacao.csv")
    metricas_a = json.loads((exp_arvore / "metricas.json").read_text(encoding="utf-8"))
    meta = metricas_a["meta_acuracia"]
    por_dim = metricas_a["parada_garantida"]["validacao"]["por_dimensao"]
    q_ref = {d: por_dim[d]["media_questoes"] for d in DIMENSOES}

    br = FuncFormatter(lambda x, _: f"{x:.1f}".replace(".", ","))
    fig, eixos = plt.subplots(2, 2, figsize=(10, 7.5), sharey=True)
    for eixo, nome in zip(eixos.flat, DIMENSOES):
        for variante, est in _ESTILO_ARVORE.items():
            c = curva[(curva["variante"] == variante) & (curva["dimensao"] == nome)]
            if c.empty:
                continue
            eixo.plot(
                c["media_questoes"], c["acuracia_polo"],
                color=est["cor"], marker=est["marcador"],
                markersize=7 if variante == "todos" else 4, linewidth=2, linestyle=est["linha"],
                markerfacecolor="none" if variante == "todos" else est["cor"],
                label=est["rotulo"],
            )
        eixo.plot([q_ref[nome]], [1.0], marker="X", markersize=9, color="#1f1f1d", linestyle="none",
                  label="parada garantida (sem IA)")
        eixo.annotate(f"sem IA: {q_ref[nome]:.1f}".replace(".", ","),
                      (q_ref[nome], 1.0), textcoords="offset points",
                      xytext=(-62, -14), fontsize=8, color="#1f1f1d")
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
        eixo.yaxis.set_major_formatter(br)
    eixos[0, 0].legend(loc="lower right", fontsize=9, frameon=False)
    fig.tight_layout()
    fig.savefig(caminho, dpi=200)
    plt.close(fig)


def figura_tac_tcc(exp_tac: Path, exp_arvore: Path | None, caminho) -> None:
    """Versão da curva TAC para o TCC: sem título de figura, vírgula decimal no eixo y."""
    curva = pd.read_csv(exp_tac / "curva_validacao.csv")
    metricas_t = json.loads((exp_tac / "metricas.json").read_text(encoding="utf-8"))
    meta = metricas_t["meta_acuracia"]
    por_dim = metricas_t["parada_garantida"]["validacao"]["por_dimensao"]
    q_ref = {d: por_dim[d]["media_questoes"] for d in DIMENSOES}

    arvore_curva = None
    if exp_arvore is not None and (exp_arvore / "curva_validacao.csv").exists():
        c = pd.read_csv(exp_arvore / "curva_validacao.csv")
        arvore_curva = c[c["variante"] == "dimensao"]

    br = FuncFormatter(lambda x, _: f"{x:.1f}".replace(".", ","))
    fig, eixos = plt.subplots(2, 2, figsize=(10, 7.5), sharey=True)
    for eixo, nome in zip(eixos.flat, DIMENSOES):
        if arvore_curva is not None:
            c = arvore_curva[arvore_curva["dimensao"] == nome]
            eixo.plot(c["media_questoes"], c["acuracia_polo"], color="#8c8c86", marker="^", markersize=4,
                      linewidth=1.2, label="árvore de decisão")
        for alvo, est in _ESTILO_TAC.items():
            c = curva[(curva["alvo"] == alvo) & (curva["dimensao"] == nome)].sort_values("media_questoes")
            if c.empty:
                continue
            eixo.plot(c["media_questoes"], c["acuracia_polo"], color=est["cor"], marker=est["marcador"],
                      markersize=4, linewidth=2, linestyle=est["linha"], label=est["rotulo"])
        eixo.plot([q_ref[nome]], [1.0], marker="X", markersize=9, color="#1f1f1d", linestyle="none",
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
        eixo.yaxis.set_major_formatter(br)
    eixos[0, 0].legend(loc="lower right", fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(caminho, dpi=200)
    plt.close(fig)


def figura_rl_tcc(exp_rl: Path, exp_tac: Path | None, caminho) -> None:
    """Versão da curva RL para o TCC: sem título de figura, vírgula decimal no eixo y."""
    res = pd.read_csv(exp_rl / "resultados_validacao.csv")
    gul_path = exp_rl / "gulosa_validacao.csv"
    gul = pd.read_csv(gul_path) if gul_path.exists() else None
    with open(exp_rl / "config.yaml", encoding="utf-8") as f:
        cfg_rl = yaml.safe_load(f)
    meta = cfg_rl.get("meta_acuracia", 0.9)

    tac_agg = None
    if exp_tac is not None and (exp_tac / "curva_validacao.csv").exists():
        c = pd.read_csv(exp_tac / "curva_validacao.csv")
        c = c[c["alvo"] == "escore"]
        tac_agg = c.groupby("limiar").agg(
            acc_min=("acuracia_polo", "min"),
            acc_media=("acuracia_polo", "mean"),
            questoes=("media_questoes", "sum"),
        ).reset_index()

    br = FuncFormatter(lambda x, _: f"{x:.2f}".replace(".", ","))
    fig, eixo = plt.subplots(figsize=(7.5, 5))
    if tac_agg is not None:
        eixo.plot(tac_agg["questoes"], tac_agg["acc_min"], color="#8c8c86", marker="^", markersize=4,
                  linewidth=1.5, label="TAC (cada ponto = um limiar)")
    if gul is not None:
        eixo.plot(gul["questoes"], gul["acc_min"], color="#eb6834", marker="s", markersize=4, linewidth=1.5,
                  linestyle="--", label="gulosa + classificador, sem RL (cada ponto = um limiar)")
    res_sorted = res.sort_values("questoes")
    eixo.plot(res_sorted["questoes"], res_sorted["acc_min"], color="#2a78d6", marker="o", markersize=6,
              linewidth=2, label="RL (cada ponto = um λ)")
    for _, r in res_sorted.iterrows():
        eixo.annotate(f"λ={r['lambda']:g}", (r["questoes"], r["acc_min"]), textcoords="offset points",
                      xytext=(6, -10), fontsize=8, color="#3d3d3a")
    eixo.axhline(meta, color="#6b6b66", linewidth=1, linestyle="--")
    eixo.text(0.5, meta + 0.003, f"meta {meta:.0%}", color="#3d3d3a", fontsize=8)
    eixo.set_xlabel("nº médio de questões no total (validação)")
    eixo.set_ylabel("acurácia do polo na pior dimensão")
    eixo.set_xlim(0, 44)
    eixo.set_ylim(0.7, 1.005)
    eixo.grid(color="#e5e4df", linewidth=0.8)
    eixo.spines[["top", "right"]].set_visible(False)
    eixo.legend(loc="lower right", fontsize=9, frameon=False)
    eixo.yaxis.set_major_formatter(br)
    fig.tight_layout()
    fig.savefig(caminho, dpi=200)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--experimento", default=None,
        help="caminho do experimento TAC (padrão: o último *_tac em experimentos/)",
    )
    parser.add_argument("--dados", default="dados/sintetico")
    parser.add_argument("--alvo", default="escore", choices=["escore", "theta"])
    parser.add_argument(
        "--apenas-figuras", default=None, metavar="CAMINHO",
        help="salva figuras em CAMINHO sem criar novo experimento (simulação ainda roda)",
    )
    parser.add_argument(
        "--experimento-arvore", default=None, metavar="CAMINHO",
        help="experimento *_arvore para análise por polo e figura TCC (padrão: o último em experimentos/)",
    )
    parser.add_argument(
        "--experimento-rl", default=None, metavar="CAMINHO",
        help="experimento *_rl para a figura TCC do RL (padrão: o último *_rl em experimentos/)",
    )
    args = parser.parse_args()

    # --------------------------------------------------------------------- experimento TAC
    if args.experimento:
        exp_tac = Path(args.experimento)
    else:
        candidatos = sorted(Path("experimentos").glob("*_tac"))
        if not candidatos:
            raise FileNotFoundError("Nenhum experimento *_tac encontrado em experimentos/")
        exp_tac = candidatos[-1]
    print(f"Experimento TAC : {exp_tac}")

    tac: TAC = joblib.load(exp_tac / "modelo_tac.joblib")
    metricas_orig = json.loads((exp_tac / "metricas.json").read_text(encoding="utf-8"))
    limiares_dict: dict = metricas_orig["alvos"][args.alvo]["limiares_escolhidos"]
    limiares = [limiares_dict[d] for d in DIMENSOES]
    print(f"Alvo            : {args.alvo}")
    print(f"Limiares (val.) : {dict(zip(DIMENSOES, limiares))}\n")

    # --------------------------------------------------------------------- experimentos auxiliares
    if args.experimento_arvore:
        exp_arvore: Path | None = Path(args.experimento_arvore)
    else:
        cands_a = sorted(Path("experimentos").glob("*_arvore"))
        exp_arvore = cands_a[-1] if cands_a else None

    if args.experimento_rl:
        exp_rl: Path | None = Path(args.experimento_rl)
    else:
        cands_rl = sorted(Path("experimentos").glob("*_rl"))
        exp_rl = cands_rl[-1] if cands_rl else None

    # --------------------------------------------------------------------- dados de teste
    teste = carregar_conjunto("teste", args.dados)
    X_te = respostas(teste)
    g_te = gabarito(teste)
    n = len(X_te)
    print(f"Conjunto de teste: {n} alunos\n")

    # --------------------------------------------------------------------- simulação TAC
    print("Simulando o TAC no conjunto de TESTE...")
    trajs = []
    for d in range(4):
        trajs.append(tac.trajetoria(X_te, d))
        print(f"  {DIMENSOES[d]}: pronto")

    partes = [TAC.aplicar_limiar(trajs[d], limiares[d], args.alvo) for d in range(4)]
    polo_prev = np.stack([p["polo"] for p in partes], axis=1)    # (n, 4)
    n_q = np.stack([p["n_questoes"] for p in partes], axis=1)    # (n, 4)
    n_total = n_q.sum(axis=1)                                     # (n,) questões distintas

    polo_real = g_te["polo"]             # (n, 4)
    intens_real = g_te["intensidade"]    # (n, 4)

    # --------------------------------------------------------------------- acurácia + IC
    print("\n" + "=" * 65)
    print("ACURÁCIA POR DIMENSÃO NO TESTE  (IC 95 % Wilson)")
    print("=" * 65)
    dim_stats: dict = {}
    for d, nome in enumerate(DIMENSOES):
        correto = polo_real[:, d] == polo_prev[:, d]
        acc = float(correto.mean())
        ic_low, ic_high = wilson_ic95(int(correto.sum()), n)
        polos_nome = "/".join(POLOS[nome])
        print(f"  {nome:8s} ({polos_nome:22s}):  {acc:.4f}  IC95% [{ic_low:.4f}, {ic_high:.4f}]")
        dim_stats[nome] = {
            "acuracia": round(acc, 4),
            "ic95_low": ic_low,
            "ic95_high": ic_high,
            "n_acertos": int(correto.sum()),
            "n_total": n,
        }

    # --------------------------------------------------------------------- perfil completo
    print("\n" + "=" * 65)
    print("ACURÁCIA DO PERFIL COMPLETO  (4 dimensões certas de uma vez)")
    print("=" * 65)
    perfil_certo = (polo_real == polo_prev).all(axis=1)
    acc_perfil = float(perfil_certo.mean())
    ic_p_low, ic_p_high = wilson_ic95(int(perfil_certo.sum()), n)
    print(f"  Acurácia : {acc_perfil:.4f}  IC95% [{ic_p_low:.4f}, {ic_p_high:.4f}]")
    print(f"  ({perfil_certo.sum()} de {n} alunos com as 4 dimensões corretas)")

    # --------------------------------------------------------------------- distribuição de erros
    print("\n" + "=" * 65)
    print("DISTRIBUIÇÃO DE ERROS POR ALUNO  (dimensões erradas)")
    print("=" * 65)
    erros_por_aluno = (polo_real != polo_prev).sum(axis=1)
    dist_erros: dict = {}
    for k in range(5):
        qtd = int((erros_por_aluno == k).sum())
        pct = 100.0 * qtd / n
        print(f"  {k} dimensões erradas :  {qtd:5d} alunos  ({pct:.1f} %)")
        dist_erros[k] = {"alunos": qtd, "percentual": round(pct, 2)}

    # --------------------------------------------------------------------- acurácia por intensidade
    print("\n" + "=" * 65)
    print("ACURÁCIA POR FAIXA DE INTENSIDADE")
    print("=" * 65)
    intens_stats: dict = {}
    for d, nome in enumerate(DIMENSOES):
        correto = polo_real[:, d] == polo_prev[:, d]
        faixas: dict = {}
        partes_linha = []
        for k, nome_faixa in NOMES_INTENSIDADE.items():
            mask = intens_real[:, d] == k
            if mask.sum() == 0:
                faixas[nome_faixa] = None
                partes_linha.append(f"{nome_faixa}: —")
            else:
                acc_f = float(correto[mask].mean())
                faixas[nome_faixa] = {"acuracia": round(acc_f, 4), "n": int(mask.sum())}
                partes_linha.append(f"{nome_faixa}: {acc_f:.4f} (n={mask.sum()})")
        print(f"  {nome:8s}  " + "  |  ".join(partes_linha))
        intens_stats[nome] = faixas

    # --------------------------------------------------------------------- distribuição de questões
    print("\n" + "=" * 65)
    print("DISTRIBUIÇÃO DO Nº DE QUESTÕES TOTAIS POR ALUNO")
    print("=" * 65)
    p10, med, p90 = (float(x) for x in np.percentile(n_total, [10, 50, 90]))
    print(f"  Média   : {n_total.mean():.2f}")
    print(f"  Mediana : {med:.1f}")
    print(f"  p10     : {p10:.1f}")
    print(f"  p90     : {p90:.1f}")
    print(f"  Mín     : {n_total.min()}")
    print(f"  Máx     : {n_total.max()}")
    print("  Média por dimensão:")
    for d, nome in enumerate(DIMENSOES):
        print(f"    {nome}: {n_q[:, d].mean():.3f}")
    q_stats = {
        "media": round(float(n_total.mean()), 3),
        "mediana": med,
        "p10": p10,
        "p90": p90,
        "min": int(n_total.min()),
        "max": int(n_total.max()),
        "desvio": round(float(n_total.std()), 3),
        "por_dimensao": {d: round(float(n_q[:, i].mean()), 3) for i, d in enumerate(DIMENSOES)},
    }

    # --------------------------------------------------------------------- verificação do dossiê
    print("\n" + "=" * 65)
    print("VERIFICAÇÃO DOS NÚMEROS DO DOSSIÊ  (D14 / D19)")
    print("=" * 65)
    ACC_DOSSIE = {"ati_ref": 0.901, "sen_int": 0.922, "vis_ver": 0.921, "seq_glo": 0.924}
    MEDIA_DOSSIE = 14.81
    tudo_ok = True
    for nome, esperado in ACC_DOSSIE.items():
        obtido = dim_stats[nome]["acuracia"]
        ok = abs(obtido - esperado) < 0.001
        flag = "OK" if ok else "DIVERGE"
        print(f"  acurácia {nome:<8s}: esperado {esperado:.3f}, obtido {obtido:.4f}  {flag}")
        if not ok:
            tudo_ok = False
    ok_media = abs(q_stats["media"] - MEDIA_DOSSIE) < 0.01
    flag = "OK" if ok_media else "DIVERGE"
    print(f"  questões média  : esperado {MEDIA_DOSSIE:.2f}, obtido {q_stats['media']:.3f}  {flag}")
    if not ok_media:
        tudo_ok = False
    if not tudo_ok:
        print("\n*** ATENÇÃO: números divergem do dossiê. PARANDO sem criar o experimento. ***")
        raise SystemExit(1)
    print("  Todos os números batem com o dossiê.")

    # --------------------------------------------------------------------- árvore de decisão
    arvore_prev_polo: np.ndarray | None = None
    if exp_arvore and (exp_arvore / "modelo_dimensao.joblib").exists():
        arvore_modelo = joblib.load(exp_arvore / "modelo_dimensao.joblib")
        arvore_prev_polo = arvore_modelo.prever(X_te)["polo"]   # (n, 4)
        print(f"\nÁrvore de decisão carregada : {exp_arvore}")
    else:
        print("\n(Árvore não encontrada; análise por polo só para o TAC.)")

    # --------------------------------------------------------------------- acurácia por polo
    polo_stats_tac: dict = {}
    for d, nome in enumerate(DIMENSOES):
        polo_a_nome, polo_b_nome = POLOS[nome]
        polo_stats_tac[nome] = acuracia_por_polo(
            polo_real[:, d], polo_prev[:, d], polo_a_nome, polo_b_nome)
    _imprimir_polo_tabela(f"TAC (alvo: {args.alvo})", polo_stats_tac)

    polo_stats_arvore: dict = {}
    if arvore_prev_polo is not None:
        for d, nome in enumerate(DIMENSOES):
            polo_a_nome, polo_b_nome = POLOS[nome]
            polo_stats_arvore[nome] = acuracia_por_polo(
                polo_real[:, d], arvore_prev_polo[:, d], polo_a_nome, polo_b_nome)
        _imprimir_polo_tabela("Árvore de decisão", polo_stats_arvore)

    # --------------------------------------------------------------------- serrilhado no histograma
    print("\n" + "=" * 65)
    print("INVESTIGAÇÃO DO PADRÃO SERRILHADO (mod 3)")
    print("=" * 65)
    print("  Resíduo de n_total (mod 3):")
    for r in range(3):
        qtd = int((n_total % 3 == r).sum())
        pct = 100.0 * qtd / n
        print(f"    n == {r} (mod 3) : {qtd:6d} alunos ({pct:.1f} %)")
    print("  Por dimensão — moda e valores mais frequentes:")
    for i, dim in enumerate(DIMENSOES):
        nq_d = n_q[:, i]
        vals, cnts = np.unique(nq_d, return_counts=True)
        top3 = vals[np.argsort(-cnts)[:3]]
        moda = int(top3[0])
        print(f"    {dim}: moda={moda} (mod 3={moda%3})  "
              f"top-3={[int(x) for x in top3]}  min={int(nq_d.min())}  max={int(nq_d.max())}")
        for r in range(3):
            qtd = int((nq_d % 3 == r).sum())
            pct = 100.0 * qtd / n
            print(f"      == {r} (mod 3): {qtd:6d} alunos ({pct:.1f} %)")
    combos, combo_cnts = np.unique(n_q, axis=0, return_counts=True)
    ordem = np.argsort(-combo_cnts)
    print("  Top-5 combinacoes (ati_ref, sen_int, vis_ver, seq_glo) -> total  (mod 3):")
    for i in range(min(5, len(ordem))):
        c = combos[ordem[i]]
        s = int(c.sum())
        print(f"    {tuple(int(x) for x in c)} -> {s:3d}  (mod 3={s%3})  n={combo_cnts[ordem[i]]}")

    # --------------------------------------------------------------------- figuras
    br1 = FuncFormatter(lambda x, _: f"{x:.1f}".replace(".", ","))

    if args.apenas_figuras:
        dir_fig = Path(args.apenas_figuras)
        print(f"\nSalvando figuras em: {dir_fig}  (modo --apenas-figuras)")
    else:
        cfg = {
            "nome_experimento": "analise_tac",
            "experimento_tac": str(exp_tac),
            "experimento_arvore": str(exp_arvore) if exp_arvore else None,
            "experimento_rl": str(exp_rl) if exp_rl else None,
            "alvo": args.alvo,
            "limiares_escolhidos": limiares_dict,
            "diretorio_dados": args.dados,
        }
        exp = Experimento("analise_tac", cfg)
        dir_fig = exp.dir
        print(f"\nSalvando resultados em: {exp.dir}")

    def _cam(nome: str) -> Path:
        return dir_fig / nome

    # --- figura 1: histograma de questões
    media_str = f"média = {n_total.mean():.1f}".replace(".", ",")
    mediana_str = f"mediana = {int(med)}"
    fig, ax = plt.subplots(figsize=(8, 4))
    contagens = np.bincount(n_total, minlength=45)
    ax.bar(np.arange(len(contagens)), contagens, color="#2B59C3", width=0.8)
    ax.axvline(n_total.mean(), color="#D64545", linewidth=1.5, linestyle="--", label=media_str)
    ax.axvline(med, color="#1E9E6A", linewidth=1.5, linestyle=":", label=mediana_str)
    ax.set_xlabel("Nº de questões respondidas")
    ax.set_ylabel("Alunos")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#DCE6F2", linewidth=0.8)
    fig.tight_layout()
    fig_q = _cam("questoes_por_aluno.png")
    fig.savefig(fig_q, dpi=200)
    plt.close(fig)
    print(f"  questoes_por_aluno.png      -> {fig_q}")

    # --- figura 2: acerto por faixa de intensidade
    nomes_faixa = list(NOMES_INTENSIDADE.values())
    cores_faixa = ["#F5D90A", "#2B59C3", "#1B2A41"]
    fig, eixos = plt.subplots(1, 4, figsize=(12, 4), sharey=True)
    for ax, (d, nome) in zip(eixos, enumerate(DIMENSOES)):
        correto = polo_real[:, d] == polo_prev[:, d]
        accs_faixa, ns_faixa = [], []
        for k in range(3):
            mask = intens_real[:, d] == k
            accs_faixa.append(float(correto[mask].mean()) if mask.sum() > 0 else 0.0)
            ns_faixa.append(int(mask.sum()))
        bars = ax.bar(nomes_faixa, accs_faixa, color=cores_faixa, width=0.5)
        for bar, n_f in zip(bars, ns_faixa):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                    f"n={n_f}", ha="center", va="bottom", fontsize=8)
        ax.axhline(0.9, color="#D64545", linewidth=1, linestyle="--")
        ax.set_title(f"{POLOS[nome][0]}/{POLOS[nome][1]}", fontsize=10)
        ax.set_ylim(0, 1.08)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color="#DCE6F2", linewidth=0.8)
    eixos[0].set_ylabel("Acurácia do polo")
    eixos[0].yaxis.set_major_formatter(br1)
    fig.tight_layout()
    fig_i = _cam("acerto_por_intensidade.png")
    fig.savefig(fig_i, dpi=200)
    plt.close(fig)
    print(f"  acerto_por_intensidade.png  -> {fig_i}")

    # --- acuracia_por_polo.csv
    linhas_polo = []
    for nome in DIMENSOES:
        polo_a_nome, polo_b_nome = POLOS[nome]
        for modelo_nome, stats_dict in (("tac", polo_stats_tac), ("arvore", polo_stats_arvore)):
            if not stats_dict:
                continue
            stats = stats_dict[nome]
            for polo_nome in (polo_a_nome, polo_b_nome):
                v = stats[polo_nome]
                linhas_polo.append({
                    "modelo": modelo_nome, "dimensao": nome, "polo": polo_nome,
                    "n": v["n"], "percentual": v["percentual"],
                    "acuracia": v["acuracia"],
                    "ic95_low": v["ic95_low"], "ic95_high": v["ic95_high"],
                    "acuracia_balanceada": stats["acuracia_balanceada"],
                })
    csv_polo = _cam("acuracia_por_polo.csv")
    pd.DataFrame(linhas_polo).to_csv(csv_polo, index=False)
    print(f"  acuracia_por_polo.csv       -> {csv_polo}")

    # --- figuras TCC (sem título de figura, vírgula decimal nos eixos)
    if exp_arvore and (exp_arvore / "curva_validacao.csv").exists():
        fig_at = _cam("curva_arvore_tcc.png")
        figura_arvore_tcc(exp_arvore, fig_at)
        print(f"  curva_arvore_tcc.png       -> {fig_at}")

    fig_tt = _cam("curva_tac_tcc.png")
    figura_tac_tcc(exp_tac, exp_arvore, fig_tt)
    print(f"  curva_tac_tcc.png          -> {fig_tt}")

    if exp_rl and (exp_rl / "resultados_validacao.csv").exists():
        fig_rt = _cam("curva_rl_tcc.png")
        figura_rl_tcc(exp_rl, exp_tac, fig_rt)
        print(f"  curva_rl_tcc.png          -> {fig_rt}")

    if args.apenas_figuras:
        print("Concluído (apenas figuras).")
        return

    # --- analise.json
    analise = {
        "n_alunos_teste": n,
        "acuracia_por_dimensao": dim_stats,
        "acuracia_por_polo_tac": polo_stats_tac,
        **( {"acuracia_por_polo_arvore": polo_stats_arvore} if polo_stats_arvore else {} ),
        "acuracia_perfil_completo": {
            "acuracia": round(acc_perfil, 4),
            "ic95_low": ic_p_low,
            "ic95_high": ic_p_high,
            "n_acertos": int(perfil_certo.sum()),
        },
        "distribuicao_erros": dist_erros,
        "acuracia_por_intensidade": intens_stats,
        "questoes": q_stats,
    }
    resumo = {
        "n_alunos": n,
        "acc_perfil": round(acc_perfil, 4),
        "media_questoes": q_stats["media"],
        "mediana_questoes": q_stats["mediana"],
        "acc_min_dim": min(v["acuracia"] for v in dim_stats.values()),
        "bal_acc_min_tac": min(
            v["acuracia_balanceada"] for v in polo_stats_tac.values()
            if v["acuracia_balanceada"] is not None
        ),
    }
    exp.finalizar(analise, resumo=resumo)
    print(f"\nPasta do experimento: {exp.dir}")
    print("Concluído.")


if __name__ == "__main__":
    main()
