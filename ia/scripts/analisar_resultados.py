"""Análise final do TAC escolhido (D19 / D20): métricas completas no conjunto de TESTE.

Uso (de dentro da pasta ia/):
    python scripts/analisar_resultados.py [--experimento experimentos/2026-10-25_092249_tac]
                                          [--dados dados/sintetico]
                                          [--alvo escore]

O que faz:
  1. Lê o modelo TAC e os limiares escolhidos na validação do experimento indicado.
  2. Re-simula o TAC no TESTE com esses limiares.
  3. Calcula métricas que não estavam no metricas.json do treino:
     - IC de 95% (Wilson) da acurácia de cada dimensão;
     - acurácia do PERFIL COMPLETO (4 dimensões certas de uma vez);
     - distribuição de erros por aluno (0 a 4 dimensões erradas);
     - distribuição completa do nº de questões (mediana, p10, p90, mín, máx).
  4. Gera questoes_por_aluno.png e acerto_por_intensidade.png.
  5. Salva analise.json e cria entrada no registro de experimentos.
  6. Para se qualquer número divergir dos valores já registrados no dossiê.

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
    args = parser.parse_args()

    # --------------------------------------------------------------------- experimento
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

    # --------------------------------------------------------------------- dados de teste
    teste = carregar_conjunto("teste", args.dados)
    X_te = respostas(teste)
    g_te = gabarito(teste)
    n = len(X_te)
    print(f"Conjunto de teste: {n} alunos\n")

    # --------------------------------------------------------------------- simulação
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

    if args.apenas_figuras:
        print("Concluído (apenas figuras).")
        return

    # --- analise.json
    analise = {
        "n_alunos_teste": n,
        "acuracia_por_dimensao": dim_stats,
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
    }
    exp.finalizar(analise, resumo=resumo)
    print(f"\nPasta do experimento: {exp.dir}")
    print("Concluído.")


if __name__ == "__main__":
    main()
