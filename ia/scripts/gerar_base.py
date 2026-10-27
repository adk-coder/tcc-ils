"""Etapa 1 — gera a base sintética do ILS e divide em treino/validação/teste.

Uso (de dentro da pasta ia/):
    python scripts/gerar_base.py --config configs/gerador.yaml

Saídas:
    dados/sintetico/{treino,validacao,teste}.parquet
    dados/sintetico/itens_calibrados.csv
    experimentos/<data>_base_sintetica/   (config, ambiente, métricas, tabelas)
    experimentos/registro.csv             (uma linha nova)
"""

import argparse
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from ils_adaptativo.calibracao import calibrar, calibrar_correlacao_tracos
from ils_adaptativo.constantes import COLUNAS_ITENS, DIMENSOES, N_ITENS, dimensao_do_item, itens_da_dimensao
from ils_adaptativo.escore import NOMES_INTENSIDADE
from ils_adaptativo.gerador import alfa_cronbach, dividir, gerar_respondentes
from ils_adaptativo.registro import Experimento


def carregar_itens(caminho: str) -> dict:
    with open(caminho, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    itens = cfg["itens"]
    faltando = set(range(1, N_ITENS + 1)) - set(itens)
    if faltando:
        raise ValueError(f"itens sem parâmetros em {caminho}: {sorted(faltando)}")
    cfg["r"] = np.array([itens[i]["r"] for i in range(1, N_ITENS + 1)], dtype=float)
    cfg["p"] = np.array([itens[i].get("p", 0.5) for i in range(1, N_ITENS + 1)], dtype=float)
    return cfg


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def resumo_conjunto(df: pd.DataFrame) -> dict:
    """Estatísticas descritivas de um conjunto (para conferir que a divisão ficou equilibrada)."""
    saida = {"n": len(df)}
    for nome in DIMENSOES:
        intens = df[f"intensidade_{nome}"].value_counts(normalize=True).sort_index()
        saida[nome] = {
            "prop_polo_a": round(float(df[f"polo_{nome}"].mean()), 4),
            "escore_medio": round(float(df[f"escore_{nome}"].mean()), 3),
            "prop_intensidade": {NOMES_INTENSIDADE[k]: round(float(v), 4) for k, v in intens.items()},
        }
    return saida


def salvar(df: pd.DataFrame, caminho: Path, formato: str) -> Path:
    if formato == "parquet":
        caminho = caminho.with_suffix(".parquet")
        df.to_parquet(caminho, index=False)
    else:
        caminho = caminho.with_suffix(".csv")
        df.to_csv(caminho, index=False)
    return caminho


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="configs/gerador.yaml")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    itens = carregar_itens(cfg["arquivo_itens"])

    if itens["status"] != "PUBLICADO":
        print("\n" + "!" * 70)
        print("  AVISO: configs/itens_ils.yaml está com status", itens["status"])
        print("  A base gerada NÃO usa os valores publicados e não deve ir para o TCC.")
        print("!" * 70 + "\n")

    # Uma seed "mãe" gera quatro fluxos aleatórios independentes. Assim, mudar
    # por exemplo o tamanho da amostra de calibração não altera os θ sorteados.
    fluxos = np.random.SeedSequence(cfg["seed"]).spawn(4)
    rng_calib, rng_theta, rng_resp, rng_div = (np.random.default_rng(s) for s in fluxos)

    exp = Experimento(cfg["nome_experimento"], {**cfg, "itens_status": itens["status"],
                                                "itens_tipo_correlacao": itens["tipo_correlacao"]})
    print(f"Experimento: {exp.dir}")

    # 1) Calibração de a_i, b_i
    c = cfg["calibracao"]
    print("Calibrando parâmetros dos itens...")
    par = calibrar(itens["r"], itens["p"], itens["tipo_correlacao"], rng_calib,
                   n_amostra=c["n_amostra"], max_iteracoes=c["max_iteracoes"],
                   tolerancia=c["tolerancia"], a_maximo=c["a_maximo"], r_minimo=c["r_minimo"])
    itens_no_piso = [int(i) + 1 for i in np.where(par.r_usado != par.r_alvo)[0]]
    print(f"  convergiu={par.convergiu} em {par.iteracoes} iterações; "
          f"maior erro em r = {np.abs(par.r_obtido - par.r_usado).max():.4f}")
    if itens_no_piso:
        print(f"  itens com r publicado abaixo de r_minimo (modelados como quase aleatórios): {itens_no_piso}")

    print("Calibrando correlação entre dimensões...")
    sigma, rel_sigma = calibrar_correlacao_tracos(par.a, par.b, cfg.get("correlacoes_escores_alvo") or {},
                                                  rng_calib, n_amostra=c["n_amostra"])
    for nome_par, v in rel_sigma.items():
        print(f"  {nome_par}: ρ(θ) = {v['rho_theta']} → correlação dos escores = {v['obtido_escores']} "
              f"(alvo {v['alvo_escores']})")

    tabela_itens = pd.DataFrame({
        "item": np.arange(1, N_ITENS + 1),
        "dimensao": [DIMENSOES[dimensao_do_item(i)] for i in range(1, N_ITENS + 1)],
        "r_publicado": par.r_alvo, "r_usado": par.r_usado, "r_obtido": par.r_obtido.round(4),
        "p_alvo": par.p_alvo, "p_obtido": par.p_obtido.round(4),
        "a": par.a.round(4), "b": par.b.round(4),
    })

    # 2) Geração dos respondentes
    print(f"Gerando {cfg['n_respondentes']} respondentes...")
    df = gerar_respondentes(cfg["n_respondentes"], par.a, par.b, sigma, rng_theta, rng_resp)

    # 3) Divisão ANTES de qualquer modelagem
    conjuntos = dividir(df, cfg["divisao"], rng_div)

    # 4) Salvamento
    saida = Path(cfg["diretorio_saida"])
    saida.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for nome, parte in conjuntos.items():
        caminho = salvar(parte, saida / nome, cfg["formato"])
        hashes[caminho.name] = sha256(caminho)
        print(f"  {caminho}  ({len(parte)} linhas)")
    tabela_itens.to_csv(saida / "itens_calibrados.csv", index=False)
    tabela_itens.to_csv(exp.caminho("itens_calibrados.csv"), index=False)

    # 5) Métricas de validação da base
    respostas = df[COLUNAS_ITENS].to_numpy()
    alfas = {nome: round(alfa_cronbach(respostas[:, [i - 1 for i in itens_da_dimensao(d)]]), 4)
             for d, nome in enumerate(DIMENSOES)}
    corr_escores = df[[f"escore_{n}" for n in DIMENSOES]].corr().round(4)

    metricas = {
        "itens_status": itens["status"],
        "calibracao": {
            "convergiu": par.convergiu,
            "iteracoes": par.iteracoes,
            "erro_max_r": round(float(np.abs(par.r_obtido - par.r_usado).max()), 5),
            "erro_max_p": round(float(np.abs(par.p_obtido - par.p_alvo).max()), 5),
            "itens_no_piso_r_minimo": itens_no_piso,
        },
        "correlacao_tracos": {"matriz_sigma": sigma.round(4).tolist(), "pares": rel_sigma},
        "alfa_cronbach": alfas,
        "alfa_referencia": cfg.get("alfa_referencia"),
        "correlacao_entre_escores": corr_escores.to_dict(),
        "conjuntos": {nome: resumo_conjunto(parte) for nome, parte in conjuntos.items()},
        "sha256_arquivos": hashes,
    }
    exp.finalizar(metricas, resumo={"status_itens": itens["status"], "alfas": alfas,
                                    "n": cfg["n_respondentes"]})

    print("\nAlfa de Cronbach (gerado × referência):")
    for nome in DIMENSOES:
        ref = (cfg.get("alfa_referencia") or {}).get(nome)
        print(f"  {nome}: {alfas[nome]:.3f} × {ref}")
    for nome, parte in conjuntos.items():
        props = {d: round(float(parte[f'polo_{d}'].mean()), 3) for d in DIMENSOES}
        print(f"  {nome:10s} proporção do polo 'a': {props}")
    print(f"\nRegistro salvo em {exp.dir}")


if __name__ == "__main__":
    main()
