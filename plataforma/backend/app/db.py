"""Conexão com o banco. Em produção: PostgreSQL; em testes: SQLite em memória."""

from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from .config import config

# check_same_thread só existe no SQLite; o FastAPI usa várias threads
_sqlite = config.database_url.startswith("sqlite")
_args = {"check_same_thread": False} if _sqlite else {}
# pool_pre_ping: testa a conexão antes de usar. O Neon (gratuito) desliga o banco depois de
# alguns minutos parado e derruba as conexões abertas; sem isso, a 1ª requisição daria erro.
engine = create_engine(config.database_url, connect_args=_args, pool_pre_ping=not _sqlite)


def criar_tabelas() -> None:
    """Cria as tabelas que ainda não existem (suficiente para o TCC; sem migrações)."""
    from . import modelos  # noqa: F401  (registra os modelos no metadata)
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    """Dependência do FastAPI: uma sessão de banco por requisição."""
    with Session(engine) as sessao:
        yield sessao
