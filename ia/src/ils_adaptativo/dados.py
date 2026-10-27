"""Leitura dos conjuntos treino / validação / teste gerados na etapa 1."""

from pathlib import Path

import numpy as np
import pandas as pd

from .constantes import COLUNAS_ITENS, DIMENSOES


def carregar_conjunto(nome: str, diretorio: str | Path = "dados/sintetico") -> pd.DataFrame:
    """Lê dados/sintetico/<nome>.parquet (ou .csv, se o parquet não existir)."""
    diretorio = Path(diretorio)
    parquet, csv = diretorio / f"{nome}.parquet", diretorio / f"{nome}.csv"
    if parquet.exists():
        return pd.read_parquet(parquet)
    if csv.exists():
        return pd.read_csv(csv)
    raise FileNotFoundError(f"conjunto '{nome}' não encontrado em {diretorio}. Rode scripts/gerar_base.py antes.")


def respostas(df: pd.DataFrame) -> np.ndarray:
    """Matriz (n, 44) de respostas 0/1 — a ÚNICA entrada permitida para os modelos."""
    return df[COLUNAS_ITENS].to_numpy(dtype=np.int8)


def gabarito(df: pd.DataFrame) -> dict[str, np.ndarray]:
    """Escore, polo e intensidade do ILS completo, cada um como matriz (n, 4)."""
    return {
        campo: df[[f"{campo}_{d}" for d in DIMENSOES]].to_numpy()
        for campo in ("escore", "polo", "intensidade")
    }
