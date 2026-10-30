"""Exporta o modelo do TAC para a plataforma (backend).

Uso (de dentro da pasta ia/):
    python scripts/exportar_modelo.py
    python scripts/exportar_modelo.py --experimento experimentos/2026-10-20_101500_tac
    python scripts/exportar_modelo.py --limiar-projeto      # usa 95% em todas as dimensões

Lê o experimento do TAC (por padrão, o mais recente em experimentos/*_tac/) e grava
plataforma/backend/app/ils/modelo_tac.json com:
  - a e b de cada item, estimados com girth SÓ no treino (itens_girth.csv);
  - o limiar de parada de cada dimensão escolhido NA VALIDAÇÃO (alvo "escore");
  - a grade de θ usada; e, para rastreabilidade, o nome do experimento e o
    desempenho no TESTE do limiar exportado.
Nada é recalculado aqui: a plataforma usa exatamente o modelo que foi avaliado.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

from ils_adaptativo.constantes import DIMENSOES, N_ITENS

SAIDA_PADRAO = Path(__file__).resolve().parents[2] / "plataforma" / "backend" / "app" / "ils" / "modelo_tac.json"


def montar_modelo(exp: Path, limiar_projeto: bool = False) -> dict:
    with open(exp / "config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    with open(exp / "metricas.json", encoding="utf-8") as f:
        metricas = json.load(f)
    itens = pd.read_csv(exp / "itens_girth.csv").sort_values("item")
    if list(itens["item"]) != list(range(1, N_ITENS + 1)):
        raise ValueError("itens_girth.csv precisa ter os itens 1 a 44")

    bloco = metricas["alvos"]["escore"]
    if limiar_projeto:
        limiares = {nome: float(cfg["limiar_projeto"]) for nome in DIMENSOES}
        avaliacao = bloco["limiar_projeto"]["teste"]
    else:
        limiares = {nome: float(bloco["limiares_escolhidos"][nome]) for nome in DIMENSOES}
        avaliacao = bloco["limiar_escolhido"]["teste"]

    return {
        "descricao": "TAC com TRI (2PL), alvo = polo do ILS completo. Gerado por ia/scripts/exportar_modelo.py.",
        "experimento": exp.name,
        "exportado_em": datetime.now().isoformat(timespec="seconds"),
        "alvo": "escore",
        "regra_limiar": "projeto (95%)" if limiar_projeto else "escolhido na validação (meta de acurácia)",
        "grade": {"pontos": int(cfg["grade_theta"]["pontos"]), "maximo": float(cfg["grade_theta"]["maximo"])},
        "limiares": limiares,
        "a": [round(float(x), 6) for x in itens["a_girth"]],
        "b": [round(float(x), 6) for x in itens["b_girth"]],
        "desempenho_teste": {
            "media_questoes_total": avaliacao["geral"]["media_questoes_total"],
            "acuracia_polo": {k: v["acuracia_polo"] for k, v in avaliacao["por_dimensao"].items()},
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--experimento", type=Path, help="pasta de um experimento do TAC (padrão: o mais recente)")
    parser.add_argument("--limiar-projeto", action="store_true", help="usa o limiar de 95%% em vez do escolhido")
    parser.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    args = parser.parse_args()

    exp = args.experimento
    if exp is None:
        candidatos = sorted(Path("experimentos").glob("*_tac"))
        if not candidatos:
            raise SystemExit("Nenhum experimento do TAC em experimentos/. Rode antes: python scripts/treinar_tac.py")
        exp = candidatos[-1]

    modelo = montar_modelo(exp, args.limiar_projeto)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(modelo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Experimento: {exp}")
    print(f"Limiares: {modelo['limiares']}")
    print(f"Desempenho no teste: {modelo['desempenho_teste']}")
    print(f"Gravado em: {args.saida}")


if __name__ == "__main__":
    main()
