"""Formatos de entrada e saída da API (separados das tabelas).

Separar é importante para a segurança: a resposta NUNCA inclui senha_hash, e a
entrada não deixa o cliente escolher campos como id ou datas.
"""

import re
from datetime import datetime
from typing import Literal

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


# ---------------------------------------------------------------- estilo de aprendizagem (ILS)
class PerguntaEstilo(BaseModel):
    item: int                  # número do item no ILS (1..44); o aluno não precisa ver
    numero: int                # 1ª, 2ª, 3ª... pergunta feita a este aluno
    enunciado: str
    alternativa_a: str
    alternativa_b: str


class DimensaoEstilo(BaseModel):
    dimensao: str              # ati_ref, sen_int, vis_ver, seq_glo
    polo: str                  # ex.: "ativo"
    polo_oposto: str           # ex.: "reflexivo"
    confianca: float           # P(o ILS completo daria este polo), entre 0,5 e 1
    n_questoes: int


class ItemRespondido(BaseModel):
    numero: int                # posição na sessão (1ª, 2ª...)
    item: int                  # número 1..44 no ILS
    dimensao: str              # "ati_ref" | "sen_int" | "vis_ver" | "seq_glo"
    enunciado: str             # enunciado curto da pergunta


class EstadoEstilo(BaseModel):
    status: Literal["nao_iniciado", "em_andamento", "concluido"]
    respondidas: int = 0
    partes_concluidas: int = 0          # dimensões já decididas (0 a 4)
    pergunta: PerguntaEstilo | None = None
    resultado: list[DimensaoEstilo] | None = None
    itens_respondidos: list[ItemRespondido] | None = None   # só no resultado final
    concluido_em: datetime | None = None
    textos_provisorios: bool = False    # itens.json ainda sem os textos oficiais


class RespostaEstiloEntrada(BaseModel):
    item: int = Field(ge=1, le=44)      # a pergunta que o aluno viu (confere se é a atual)
    resposta: Literal["a", "b"]


# ---------------------------------------------------------------- acompanhamento
class ErroComum(BaseModel):
    alternativa: int           # índice da alternativa errada mais marcada (0 = A)
    quantos: int


class DesempenhoExercicio(BaseModel):
    id: int
    numero: int                # 1º, 2º... dentro do módulo
    enunciado: str
    responderam: int           # alunos que tentaram pelo menos uma vez
    acerto_primeira: float | None = None   # fração que acertou de primeira (None se ninguém respondeu)
    erro_comum: ErroComum | None = None


class DesempenhoModulo(BaseModel):
    id: int
    titulo: str
    concluiram: int            # alunos que acertaram todos os exercícios do módulo
    exercicios: list[DesempenhoExercicio]


class DesempenhoAluno(BaseModel):
    id: int
    nome: str
    acertados: int
    pontos: int
    ultima_atividade: datetime | None = None


class DesempenhoSala(BaseModel):
    n_alunos: int
    total_exercicios: int
    acerto_primeira_medio: float | None = None
    modulos: list[DesempenhoModulo]
    alunos: list[DesempenhoAluno]


class Continuar(BaseModel):
    sala_id: int
    sala_nome: str
    modulo_id: int
    modulo_titulo: str
    feitos: int                # exercícios já acertados no módulo
    total: int


# ---------------------------------------------------------------- perfil da turma (professor)
class DimensaoAgregada(BaseModel):
    dimensao: str           # "ati_ref" | "sen_int" | "vis_ver" | "seq_glo"
    polo_a: str             # ex.: "ativo"
    polo_b: str             # ex.: "reflexivo"
    percentual_a: float     # 0 a 100 (arredondado para 1 casa)
    percentual_b: float     # complemento de percentual_a


class PerfilTurma(BaseModel):
    respondentes: int
    minimo_atingido: bool
    dimensoes: list[DimensaoAgregada] | None = None


# ---------------------------------------------------------------- adesivos de conquista
class Adesivo(BaseModel):
    id: str
    titulo: str
    descricao: str             # como ganhar
    meta: int
    progresso: int             # 0..meta
    ganho: bool
    ganho_em: datetime | None = None
