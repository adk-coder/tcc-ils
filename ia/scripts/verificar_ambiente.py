"""Confere se o ambiente Python está pronto para todas as etapas do TCC.

Uso (de dentro da pasta ia/, com o .venv ativado):
    python scripts/verificar_ambiente.py

Para cada biblioteca: importa, mostra a versão e roda um teste mínimo.
"""

import sys
from importlib import metadata

import numpy as np

ok = True


def checar(nome, teste):
    global ok
    try:
        teste()
        try:
            versao = metadata.version(nome)
        except metadata.PackageNotFoundError:
            versao = "?"
        print(f"  [OK]   {nome:18s} {versao}")
    except Exception as erro:  # noqa: BLE001 - queremos mostrar qualquer falha
        ok = False
        print(f"  [ERRO] {nome:18s} {type(erro).__name__}: {erro}")


def t_pandas_parquet():
    import pandas as pd
    import io
    buf = io.BytesIO()
    pd.DataFrame({"x": [1, 2]}).to_parquet(buf)


def t_girth():
    # Estima um 2PL em dados simulados pequenos: testa a compatibilidade com o numpy.
    from girth import twopl_mml
    rng = np.random.default_rng(0)
    theta = rng.standard_normal(500)
    a, b = np.full(5, 1.2), np.linspace(-1, 1, 5)
    p = 1 / (1 + np.exp(-a[:, None] * (theta[None, :] - b[:, None])))
    dados = (rng.random(p.shape) < p).astype(int)  # girth espera (itens, pessoas)
    twopl_mml(dados)


def t_catsim():
    import catsim  # noqa: F401


def t_torch():
    import torch
    torch.ones(2) @ torch.ones(2)


def t_sb3():
    from sb3_contrib import MaskablePPO  # noqa: F401


print(f"Python {sys.version.split()[0]}")
if sys.version_info[:2] != (3, 11):
    print("  [AVISO] o projeto foi pensado para Python 3.11")

checar("numpy", lambda: np.zeros(1))
checar("pandas", t_pandas_parquet)
checar("pyarrow", lambda: __import__("pyarrow"))
checar("scipy", lambda: __import__("scipy.stats"))
checar("pyyaml", lambda: __import__("yaml"))
checar("scikit-learn", lambda: __import__("sklearn.tree"))
checar("girth", t_girth)
checar("catsim", t_catsim)
checar("torch", t_torch)
checar("gymnasium", lambda: __import__("gymnasium"))
checar("stable-baselines3", lambda: __import__("stable_baselines3"))
checar("sb3-contrib", t_sb3)
checar("matplotlib", lambda: __import__("matplotlib"))
checar("ils_adaptativo", lambda: __import__("ils_adaptativo.gerador"))

print("\nTudo certo." if ok else "\nHá erros acima — copie a saída e peça ajuda.")
sys.exit(0 if ok else 1)
