"""Progresso do aluno (pontos e streak) e ranking da sala. Regras em app/gamificacao.py."""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlmodel import Session, select

from ..db import get_session
from ..deps import exigir_aluno, usuario_atual
from ..esquemas import LinhaRanking, Progresso
from ..gamificacao import FUSO, calcular_streak, nome_curto
from ..modelos import Exercicio, Matricula, Modulo, Resposta, Usuario
from .salas import sala_visivel

router = APIRouter(tags=["gamificação"])


def progresso_do_aluno(sessao: Session, aluno_id: int) -> Progresso:
    respostas = sessao.exec(select(Resposta).where(Resposta.aluno_id == aluno_id)).all()
    atual, melhor = calcular_streak([r.respondida_em for r in respostas], datetime.now(FUSO).date())
    return Progresso(pontos=sum(r.pontos_ganhos for r in respostas),
                     exercicios_acertados=len({r.exercicio_id for r in respostas if r.correta}),
                     tentativas=len(respostas), streak_atual=atual, melhor_streak=melhor)


@router.get("/eu/progresso", response_model=Progresso)
def meu_progresso(aluno: Usuario = Depends(exigir_aluno), sessao: Session = Depends(get_session)):
    return progresso_do_aluno(sessao, aluno.id)


@router.get("/salas/{sala_id}/ranking", response_model=list[LinhaRanking])
def ranking(sala_id: int, usuario: Usuario = Depends(usuario_atual), sessao: Session = Depends(get_session)):
    sala = sala_visivel(sessao, sala_id, usuario)
    eh_professor = sala.professor_id == usuario.id
    pontos_por_aluno = dict(sessao.exec(
        select(Resposta.aluno_id, func.sum(Resposta.pontos_ganhos))
        .join(Exercicio, Exercicio.id == Resposta.exercicio_id)
        .join(Modulo, Modulo.id == Exercicio.modulo_id)
        .where(Modulo.sala_id == sala.id).group_by(Resposta.aluno_id)).all())
    alunos = sessao.exec(select(Usuario).join(Matricula, Matricula.aluno_id == Usuario.id)
                         .where(Matricula.sala_id == sala.id)).all()
    ordenados = sorted(alunos, key=lambda a: (-(pontos_por_aluno.get(a.id) or 0), a.nome.lower()))
    return [LinhaRanking(posicao=i, aluno_id=a.id if eh_professor else None,
                         nome=a.nome if eh_professor else nome_curto(a.nome),
                         pontos=pontos_por_aluno.get(a.id) or 0, sou_eu=a.id == usuario.id)
            for i, a in enumerate(ordenados, start=1)]
