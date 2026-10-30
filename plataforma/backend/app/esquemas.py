"""Formatos de entrada e saída da API (separados das tabelas).

Separar é importante para a segurança: a resposta NUNCA inclui senha_hash, e a
entrada não deixa o cliente escolher campos como id ou datas.
"""

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from .modelos import Perfil

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validar_email(v: str) -> str:
    v = v.strip().lower()
    if not _EMAIL.match(v):
        raise ValueError("e-mail inválido")
    return v


class RegistroEntrada(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: str
    senha: str = Field(min_length=8, max_length=128)
    perfil: Perfil
    aceite_termos: bool  # LGPD: sem aceite explícito, não há cadastro

    _email = field_validator("email")(_validar_email)

    @field_validator("aceite_termos")
    @classmethod
    def _precisa_aceitar(cls, v: bool) -> bool:
        if not v:
            raise ValueError("é preciso aceitar os termos de uso e a política de privacidade")
        return v


class LoginEntrada(BaseModel):
    email: str
    senha: str

    _email = field_validator("email")(_validar_email)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UsuarioSaida(BaseModel):
    id: int
    nome: str
    email: str
    perfil: Perfil
    criado_em: datetime


class SalaEntrada(BaseModel):
    nome: str = Field(min_length=2, max_length=120)


class EntrarSalaEntrada(BaseModel):
    codigo: str = Field(min_length=6, max_length=8)


class SalaSaida(BaseModel):
    id: int
    nome: str
    codigo: str
    professor_id: int
    criada_em: datetime
    n_alunos: int = 0


class AlunoNaSala(BaseModel):
    id: int
    nome: str
    entrou_em: datetime


class SalaDetalhe(SalaSaida):
    professor_nome: str
    alunos: list[AlunoNaSala] = []


# ---------------------------------------------------------------- conteúdo
class ModuloEntrada(BaseModel):
    titulo: str = Field(min_length=2, max_length=150)
    conteudo: str = Field(default="", max_length=50_000)
    ordem: int = 0


class ModuloResumo(BaseModel):
    id: int
    titulo: str
    ordem: int
    n_exercicios: int
    n_acertados: int | None = None      # só para aluno: quantos já acertou


class ExercicioEntrada(BaseModel):
    enunciado: str = Field(min_length=3, max_length=5_000)
    alternativas: list[str] = Field(min_length=2, max_length=5)
    indice_correta: int
    explicacao: str = Field(default="", max_length=5_000)
    pontos: int = Field(default=10, ge=1, le=100)
    ordem: int = 0

    @model_validator(mode="after")
    def _indice_valido(self):
        if any(not a.strip() for a in self.alternativas):
            raise ValueError("alternativas não podem ser vazias")
        if not 0 <= self.indice_correta < len(self.alternativas):
            raise ValueError("indice_correta fora das alternativas")
        return self


class ExercicioProfessor(ExercicioEntrada):
    id: int
    modulo_id: int


class ExercicioAluno(BaseModel):
    """Versão para o aluno: SEM a resposta correta e SEM a explicação."""
    id: int
    enunciado: str
    alternativas: list[str]
    pontos: int
    ordem: int
    ja_respondeu: bool
    ja_acertou: bool


class ModuloDetalhe(BaseModel):
    id: int
    sala_id: int
    titulo: str
    conteudo: str
    ordem: int
    exercicios: list[ExercicioProfessor] | list[ExercicioAluno]


class RespostaEntrada(BaseModel):
    alternativa: int = Field(ge=0)


class RespostaSaida(BaseModel):
    correta: bool
    indice_correta: int
    explicacao: str
    pontos_ganhos: int
    primeira_tentativa: bool


# ---------------------------------------------------------------- gamificação
class Progresso(BaseModel):
    pontos: int
    exercicios_acertados: int
    tentativas: int
    streak_atual: int
    melhor_streak: int


class LinhaRanking(BaseModel):
    posicao: int
    aluno_id: int | None = None          # só o professor recebe o id
    nome: str
    pontos: int
    sou_eu: bool = False
