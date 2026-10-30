"""Configurações lidas de variáveis de ambiente (nada de segredo dentro do código).

Variáveis:
  DATABASE_URL     ex.: postgresql+psycopg://tcc:tcc@localhost:5432/tcc
                   (padrão: SQLite local, só para desenvolvimento rápido).
                   Endereços "postgres://" ou "postgresql://" (como os que o Neon
                   e o Render entregam) são convertidos para o driver psycopg 3.
  SEGREDO_JWT      chave para assinar os tokens (OBRIGATÓRIA fora do modo dev)
  MINUTOS_TOKEN    validade do token de acesso (padrão 60)
  ORIGENS_CORS     endereços do frontend separados por vírgula
                   (padrão http://localhost:3000, onde roda o Nuxt)
  AMBIENTE         "dev" (padrão) ou "producao"
"""

import os
import warnings
from dataclasses import dataclass, field

SEGREDO_DEV = "segredo-de-desenvolvimento-troque-em-producao"


def normalizar_url_banco(url: str) -> str:
    """O SQLAlchemy precisa saber o driver: "postgresql://..." vira "postgresql+psycopg://..."."""
    for prefixo in ("postgres://", "postgresql://"):
        if url.startswith(prefixo):
            return "postgresql+psycopg://" + url[len(prefixo):]
    return url


@dataclass(frozen=True)
class Config:
    ambiente: str = field(default_factory=lambda: os.getenv("AMBIENTE", "dev"))
    database_url: str = field(default_factory=lambda: normalizar_url_banco(
        os.getenv("DATABASE_URL", "sqlite:///./dev.db")))
    segredo_jwt: str = field(default_factory=lambda: os.getenv("SEGREDO_JWT", SEGREDO_DEV))
    minutos_token: int = field(default_factory=lambda: int(os.getenv("MINUTOS_TOKEN", "60")))
    origens_cors: tuple[str, ...] = field(default_factory=lambda: tuple(
        o.strip() for o in os.getenv("ORIGENS_CORS", "http://localhost:3000").split(",") if o.strip()))

    def __post_init__(self):
        if self.segredo_jwt == SEGREDO_DEV:
            if self.ambiente == "producao":
                raise RuntimeError("defina SEGREDO_JWT em produção")
            warnings.warn("usando SEGREDO_JWT de desenvolvimento", stacklevel=2)


config = Config()
