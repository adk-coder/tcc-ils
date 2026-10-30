"""Tabelas do banco (SQLModel = SQLAlchemy + Pydantic na mesma classe).

LGPD — minimização de dados: o sistema guarda só o necessário para funcionar
(nome, e-mail e senha cifrada). Não guarda CPF, data de nascimento, endereço
nem telefone. O público são alunos do 9º ano (adolescentes), o que torna a
minimização ainda mais importante.
"""

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def agora() -> datetime:
    return datetime.now(timezone.utc)


class Perfil(str, Enum):
    professor = "professor"
    aluno = "aluno"


class Usuario(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nome: str = Field(max_length=120)
    email: str = Field(index=True, unique=True, max_length=254)
    senha_hash: str                                   # nunca a senha em si (ver seguranca.py)
    perfil: Perfil
    criado_em: datetime = Field(default_factory=agora)
    consentimento_em: datetime                        # quando aceitou os termos (LGPD)


class Sala(SQLModel, table=True):
    """Sala virtual: criada por um professor; alunos entram com o código de convite."""
    id: int | None = Field(default=None, primary_key=True)
    nome: str = Field(max_length=120)
    codigo: str = Field(index=True, unique=True, max_length=8)
    professor_id: int = Field(foreign_key="usuario.id", index=True)
    criada_em: datetime = Field(default_factory=agora)


class Matricula(SQLModel, table=True):
    """Ligação aluno ↔ sala (muitos para muitos)."""
    sala_id: int = Field(foreign_key="sala.id", primary_key=True)
    aluno_id: int = Field(foreign_key="usuario.id", primary_key=True)
    entrou_em: datetime = Field(default_factory=agora)


class Modulo(SQLModel, table=True):
    """Módulo de ensino de uma sala: um texto de estudo + uma lista de exercícios."""
    id: int | None = Field(default=None, primary_key=True)
    sala_id: int = Field(foreign_key="sala.id", index=True)
    titulo: str = Field(max_length=150)
    conteudo: str = ""                                # material de estudo (texto/Markdown)
    ordem: int = 0
    criado_em: datetime = Field(default_factory=agora)


class Exercicio(SQLModel, table=True):
    """Exercício de múltipla escolha (2 a 5 alternativas)."""
    id: int | None = Field(default=None, primary_key=True)
    modulo_id: int = Field(foreign_key="modulo.id", index=True)
    enunciado: str
    alternativas: list[str] = Field(sa_column=Column(JSON, nullable=False))
    indice_correta: int                               # 0 = primeira alternativa
    explicacao: str = ""                              # mostrada depois da resposta
    pontos: int = 10
    ordem: int = 0


class Resposta(SQLModel, table=True):
    """Cada tentativa de um aluno num exercício (guarda o histórico)."""
    id: int | None = Field(default=None, primary_key=True)
    exercicio_id: int = Field(foreign_key="exercicio.id", index=True)
    aluno_id: int = Field(foreign_key="usuario.id", index=True)
    alternativa: int
    correta: bool
    pontos_ganhos: int = 0                            # só a 1ª resposta certa pontua
    respondida_em: datetime = Field(default_factory=agora)
