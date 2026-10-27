"""Registro de experimentos.

Cada execução de um script cria um diretório
    experimentos/AAAA-MM-DD_HHMMSS_<nome>/
com:
    config.yaml    cópia exata da configuração usada
    ambiente.json  versão do Python, das bibliotecas, sistema, commit do git
    metricas.json  resultados numéricos
    (+ tabelas e gráficos que o script quiser salvar)
e acrescenta uma linha em experimentos/registro.csv, que funciona como um
"caderno de laboratório": dá para montar as tabelas dos capítulos de
Desenvolvimento e Resultados a partir dele.
"""

import csv
import json
import platform
import subprocess
import sys
from datetime import datetime
from importlib import metadata
from pathlib import Path

import yaml

PACOTES_RELEVANTES = [
    "numpy", "pandas", "scipy", "pyarrow", "scikit-learn", "girth", "catsim",
    "torch", "gymnasium", "stable-baselines3", "sb3-contrib",
]


def _versao(pacote: str) -> str | None:
    try:
        return metadata.version(pacote)
    except metadata.PackageNotFoundError:
        return None


def _commit_git() -> str | None:
    try:
        saida = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        sujo = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
        return saida.stdout.strip() + (" (com alterações não commitadas)" if sujo else "")
    except (OSError, subprocess.CalledProcessError):
        return None


class Experimento:
    def __init__(self, nome: str, config: dict, raiz: str | Path = "experimentos"):
        self.raiz = Path(raiz)
        self.inicio = datetime.now()
        self.nome = nome
        self.dir = self.raiz / f"{self.inicio:%Y-%m-%d_%H%M%S}_{nome}"
        self.dir.mkdir(parents=True, exist_ok=False)
        self.config = config

        with open(self.dir / "config.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)

        ambiente = {
            "inicio": self.inicio.isoformat(timespec="seconds"),
            "python": sys.version,
            "sistema": platform.platform(),
            "processador": platform.processor(),
            "commit_git": _commit_git(),
            "pacotes": {p: _versao(p) for p in PACOTES_RELEVANTES},
        }
        self._salvar_json("ambiente.json", ambiente)

    def _salvar_json(self, arquivo: str, conteudo: dict) -> None:
        with open(self.dir / arquivo, "w", encoding="utf-8") as f:
            json.dump(conteudo, f, ensure_ascii=False, indent=2)

    def caminho(self, arquivo: str) -> Path:
        """Caminho para salvar um artefato extra dentro do diretório do experimento."""
        return self.dir / arquivo

    def finalizar(self, metricas: dict, resumo: dict | None = None) -> None:
        """Salva as métricas completas e acrescenta um resumo no registro.csv.

        resumo: poucas chaves "achatadas" que valem uma coluna no registro geral.
        """
        duracao = (datetime.now() - self.inicio).total_seconds()
        metricas = {"duracao_segundos": round(duracao, 1), **metricas}
        self._salvar_json("metricas.json", metricas)

        linha = {
            "data": self.inicio.isoformat(timespec="seconds"),
            "nome": self.nome,
            "diretorio": self.dir.name,
            "seed": self.config.get("seed"),
            "duracao_s": round(duracao, 1),
            "resumo": json.dumps(resumo or {}, ensure_ascii=False),
        }
        registro = self.raiz / "registro.csv"
        novo = not registro.exists()
        with open(registro, "a", newline="", encoding="utf-8") as f:
            escritor = csv.DictWriter(f, fieldnames=list(linha))
            if novo:
                escritor.writeheader()
            escritor.writerow(linha)
