"""Etapa 4b — treina a política de seleção (MaskablePPO) para cada λ.

Uso (de dentro da pasta ia/):
    python scripts/treinar_rl.py --rapido     # conferência rápida (~minutos), não usa o teste
    python scripts/treinar_rl.py              # experimento completo (pode levar horas em CPU)

Antes do RL, avalia a política GULOSA (sem RL, mesmo classificador) para vários
limiares: é a linha de base que mostra quanto o RL acrescenta de fato.

Para cada λ:
  1. treina o MaskablePPO no ambiente (alunos do TREINO), medindo a política
     em parte da validação a cada `avaliar_a_cada` passos (curva de aprendizado);
  2. avalia a política final em toda a VALIDAÇÃO.
Depois escolhe o λ pela validação e avalia só ele no TESTE.

Saídas em experimentos/<data>_rl/:
  politica_lambda_<λ>.zip, aprendizado.csv, resultados_validacao.csv,
  curva_rl.png, metricas.json
"""

import argparse
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from sb3_contrib import MaskablePPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecMonitor

from ils_adaptativo import classificador as clf
from ils_adaptativo import politica_gulosa
from ils_adaptativo.ambiente import ClassificadorNumpy, jogar_lote
from ils_adaptativo.ambiente_gym import AmbienteILS
from ils_adaptativo.dados import carregar_conjunto, gabarito, respostas
from ils_adaptativo.metricas import avaliar
from ils_adaptativo.registro import Experimento


def achar_classificador(cfg, raiz: Path) -> Path:
    if cfg["classificador"] != "auto":
        return Path(cfg["classificador"])
    candidatos = sorted(raiz.glob("*_classificador/classificador.pt"))
    if not candidatos:
        raise FileNotFoundError("nenhum classificador encontrado; rode scripts/treinar_classificador.py antes")
    return candidatos[-1]


def politica_de(modelo: MaskablePPO):
    """Adapta a política treinada ao formato de jogar_lote (determinística: ação mais provável)."""
    def escolher(obs, mascaras):
        acoes, _ = modelo.predict(obs, action_masks=mascaras, deterministic=True)
        return np.asarray(acoes)
    return escolher


def medir(modelo, X, polo, clf_np) -> dict:
    r = jogar_lote(X, polo, clf_np, politica_de(modelo))
    m = avaliar(polo, r["polo"], r["n_questoes"], n_total=r["n_total"])
    return m


def curva_tac(raiz: Path) -> pd.DataFrame | None:
    """Curva do TAC (alvo escore) no formato acurácia mínima × total de questões."""
    candidatos = sorted(raiz.glob("*_tac/curva_validacao.csv"))
    if not candidatos:
        return None
    c = pd.read_csv(candidatos[-1])
    c = c[c["alvo"] == "escore"]
    return c.groupby("limiar").agg(acc_min=("acuracia_polo", "min"), acc_media=("acuracia_polo", "mean"),
                                   questoes=("media_questoes", "sum")).reset_index()


def grafico(res: pd.DataFrame, tac: pd.DataFrame | None, gulosa: pd.DataFrame, meta: float, caminho) -> None:
    fig, eixo = plt.subplots(figsize=(7.5, 5))
    if tac is not None:
        eixo.plot(tac["questoes"], tac["acc_min"], color="#8c8c86", marker="^", markersize=4, linewidth=1.5,
                  label="TAC (cada ponto = um limiar)")
    eixo.plot(gulosa["questoes"], gulosa["acc_min"], color="#eb6834", marker="s", markersize=4, linewidth=1.5,
              linestyle="--", label="gulosa + classificador, sem RL (cada ponto = um limiar)")
    res = res.sort_values("questoes")
    eixo.plot(res["questoes"], res["acc_min"], color="#2a78d6", marker="o", markersize=6, linewidth=2,
              label="RL (cada ponto = um λ)")
    for _, r in res.iterrows():
        eixo.annotate(f"λ={r['lambda']:g}", (r["questoes"], r["acc_min"]), textcoords="offset points",
                      xytext=(6, -10), fontsize=8, color="#3d3d3a")
    eixo.axhline(meta, color="#6b6b66", linewidth=1, linestyle="--")
    eixo.text(0.5, meta + 0.003, f"meta {meta:.0%}", color="#3d3d3a", fontsize=8)
    eixo.set_xlabel("nº médio de questões no total (validação)")
    eixo.set_ylabel("acurácia do polo na PIOR dimensão")
    eixo.set_xlim(0, 44)
    eixo.set_ylim(0.7, 1.005)
    eixo.grid(color="#e5e4df", linewidth=0.8)
    eixo.spines[["top", "right"]].set_visible(False)
    eixo.legend(loc="lower right", fontsize=9, frameon=False)
    eixo.set_title("RL × TAC: acurácia da pior dimensão × nº total de questões", fontsize=11)
    fig.tight_layout()
    fig.savefig(caminho, dpi=200)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="configs/rl.yaml")
    parser.add_argument("--rapido", action="store_true", help="conferência rápida; não usa o teste")
    parser.add_argument("--lambdas", type=float, nargs="+", help="treina só estes λ (substitui a config)")
    args = parser.parse_args()
    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    tr_cfg = dict(cfg["treino"])
    lambdas = args.lambdas or cfg["lambdas"]
    cfg["lambdas"] = lambdas
    if args.rapido:
        lambdas = lambdas[:1]
        tr_cfg.update(passos=cfg["rapido"]["passos"], avaliar_a_cada=cfg["rapido"]["avaliar_a_cada"])
        cfg["nome_experimento"] += "_rapido"

    treino, val, teste = (carregar_conjunto(n, cfg["diretorio_dados"]) for n in ("treino", "validacao", "teste"))
    X_tr, X_val, X_te = respostas(treino), respostas(val), respostas(teste)
    p_tr, p_val, p_te = gabarito(treino)["polo"], gabarito(val)["polo"], gabarito(teste)["polo"]
    if args.rapido:
        X_val, p_val = X_val[:cfg["rapido"]["n_validacao"]], p_val[:cfg["rapido"]["n_validacao"]]

    exp = Experimento(cfg["nome_experimento"], {**cfg, "modo_rapido": args.rapido})
    caminho_clf = achar_classificador(cfg, exp.raiz)
    print(f"Experimento: {exp.dir}\nClassificador: {caminho_clf}")
    clf_np = ClassificadorNumpy.de_torch(clf.carregar(caminho_clf))

    # Linha de base sem RL: política gulosa com o mesmo classificador
    print("\nPolítica gulosa (sem RL), validação:")
    linhas_gul = []
    for lim in cfg["gulosa"]["limiares"]:
        r = jogar_lote(X_val, p_val, clf_np, politica_gulosa.criar(X_tr, lim))
        g = avaliar(p_val, r["polo"], r["n_questoes"], n_total=r["n_total"])["geral"]
        linhas_gul.append({"limiar": lim, "acc_min": g["acuracia_polo_minima"],
                           "acc_media": g["acuracia_polo_media"], "questoes": g["media_questoes_total"]})
        print(f"  limiar {lim:.2f}: acurácia mín. {g['acuracia_polo_minima']:.4f} | {g['media_questoes_total']:.2f} questões")
    gul = pd.DataFrame(linhas_gul)
    gul.to_csv(exp.caminho("gulosa_validacao.csv"), index=False)
    ok_g = gul[gul["acc_min"] >= cfg["meta_acuracia"]]
    lim_gulosa = float(ok_g.sort_values("questoes")["limiar"].iloc[0]) if len(ok_g) else float(gul["limiar"].max())

    n_parcial = min(tr_cfg["n_avaliacao_parcial"], len(X_val))
    aprendizado, linhas_val, metricas_val = [], [], {}
    for i, lam in enumerate(lambdas):
        print(f"\n=== λ = {lam} ===")
        seed = cfg["seed"] + i
        fabricas = [lambda: AmbienteILS(X_tr, p_tr, clf_np, lam, cfg["recompensa"]) for _ in range(tr_cfg["n_envs"])]
        venv = VecMonitor(DummyVecEnv(fabricas))
        p = cfg["ppo"]
        modelo = MaskablePPO("MlpPolicy", venv, learning_rate=p["learning_rate"], n_steps=p["n_steps"],
                             batch_size=p["batch_size"], n_epochs=p["n_epochs"], gamma=p["gamma"],
                             gae_lambda=p["gae_lambda"], clip_range=p["clip_range"], ent_coef=p["ent_coef"],
                             policy_kwargs={"net_arch": list(p["rede"])}, seed=seed, device="cpu", verbose=0)
        print(f"  recompensa: {cfg['recompensa']}", flush=True)

        t0, feitos = time.time(), 0
        while feitos < tr_cfg["passos"]:
            bloco = min(tr_cfg["avaliar_a_cada"], tr_cfg["passos"] - feitos)
            modelo.learn(total_timesteps=bloco, reset_num_timesteps=(feitos == 0))
            feitos = modelo.num_timesteps
            m = medir(modelo, X_val[:n_parcial], p_val[:n_parcial], clf_np)["geral"]
            aprendizado.append({"lambda": lam, "passos": feitos, "segundos": round(time.time() - t0, 1),
                                "acc_min": m["acuracia_polo_minima"], "acc_media": m["acuracia_polo_media"],
                                "questoes": m["media_questoes_total"]})
            print(f"  {feitos:>9,} passos ({time.time() - t0:6.0f} s): acurácia mín. {m['acuracia_polo_minima']:.4f}"
                  f" | média {m['acuracia_polo_media']:.4f} | {m['media_questoes_total']:.2f} questões")
        modelo.save(exp.caminho(f"politica_lambda_{lam:g}.zip"))

        mv = medir(modelo, X_val, p_val, clf_np)
        metricas_val[lam] = mv
        g = mv["geral"]
        linhas_val.append({"lambda": lam, "acc_min": g["acuracia_polo_minima"], "acc_media": g["acuracia_polo_media"],
                           "questoes": g["media_questoes_total"], "todas_ge_meta": g["todas_dimensoes_ge_90"],
                           **{f"acc_{d}": v["acuracia_polo"] for d, v in mv["por_dimensao"].items()},
                           **{f"q_{d}": v["media_questoes"] for d, v in mv["por_dimensao"].items()}})
        print(f"  VALIDAÇÃO: acurácia {[v['acuracia_polo'] for v in mv['por_dimensao'].values()]} "
              f"| {g['media_questoes_total']:.2f} questões")
        venv.close()

    res = pd.DataFrame(linhas_val)
    res.to_csv(exp.caminho("resultados_validacao.csv"), index=False)
    pd.DataFrame(aprendizado).to_csv(exp.caminho("aprendizado.csv"), index=False)
    grafico(res, curva_tac(exp.raiz), gul, cfg["meta_acuracia"], exp.caminho("curva_rl.png"))

    ok = res[res["acc_min"] >= cfg["meta_acuracia"]]
    escolhido = float(ok.sort_values("questoes")["lambda"].iloc[0]) if len(ok) else \
        float(res.sort_values("acc_min")["lambda"].iloc[-1])
    print(f"\nλ escolhido na validação: {escolhido} (meta atingida: {bool(len(ok))})")

    metricas = {"lambda_escolhido": escolhido, "meta_atingida_na_validacao": bool(len(ok)),
                "classificador": str(caminho_clf), "validacao": {str(k): v for k, v in metricas_val.items()},
                "gulosa": {"limiar_escolhido": lim_gulosa, "meta_atingida_na_validacao": bool(len(ok_g))}}
    resumo = {"lambda": escolhido, "limiar_gulosa": lim_gulosa}
    if not args.rapido:
        r = jogar_lote(X_te, p_te, clf_np, politica_gulosa.criar(X_tr, lim_gulosa))
        mg = avaliar(p_te, r["polo"], r["n_questoes"], n_total=r["n_total"])
        metricas["gulosa"]["teste"] = mg
        resumo.update(gulosa_acc_min_teste=mg["geral"]["acuracia_polo_minima"],
                      gulosa_questoes_teste=mg["geral"]["media_questoes_total"])
        print(f"GULOSA (limiar {lim_gulosa}) TESTE: acurácia "
              f"{ {d: v['acuracia_polo'] for d, v in mg['por_dimensao'].items()} } | "
              f"{mg['geral']['media_questoes_total']:.2f} questões")
        modelo = MaskablePPO.load(exp.caminho(f"politica_lambda_{escolhido:g}.zip"), device="cpu")
        mt = medir(modelo, X_te, p_te, clf_np)
        metricas["teste"] = mt
        g = mt["geral"]
        resumo.update(acc_min_teste=g["acuracia_polo_minima"], questoes_teste=g["media_questoes_total"])
        print(f"RL (λ {escolhido}) TESTE: acurácia { {d: v['acuracia_polo'] for d, v in mt['por_dimensao'].items()} }")
        print(f"RL TESTE: {g['media_questoes_total']:.2f} questões em média; todas ≥ 90%: {g['todas_dimensoes_ge_90']}")
    exp.finalizar(metricas, resumo=resumo)
    print(f"\nRegistro salvo em {exp.dir}")


if __name__ == "__main__":
    main()
