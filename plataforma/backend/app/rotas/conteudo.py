"""Módulos de ensino e exercícios (o professor cria; o aluno estuda e responde)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, delete, select

from ..db import get_session
from ..deps import exigir_aluno, exigir_professor, usuario_atual
from ..esquemas import (ExercicioAluno, ExercicioEntrada, ExercicioProfessor, ModuloDetalhe, ModuloEntrada,
                        ModuloResumo, RespostaEntrada, RespostaSaida)
from ..modelos import Exercicio, Modulo, Perfil, Resposta, Usuario
from .salas import sala_visivel

router = APIRouter(tags=["conteúdo"])


# ------------------------------------------------------------------ auxiliares
def _modulo_visivel(sessao: Session, modulo_id: int, usuario: Usuario) -> Modulo:
    modulo = sessao.get(Modulo, modulo_id)
    if modulo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "módulo não encontrado")
    sala_visivel(sessao, modulo.sala_id, usuario)        # 404 se não puder ver a sala
    return modulo


def _modulo_do_professor(sessao: Session, modulo_id: int, prof: Usuario) -> Modulo:
    modulo = _modulo_visivel(sessao, modulo_id, prof)    # professor só "vê" as próprias salas
    return modulo


def _exercicio_visivel(sessao: Session, exercicio_id: int, usuario: Usuario) -> tuple[Exercicio, Modulo]:
    exercicio = sessao.get(Exercicio, exercicio_id)
    if exercicio is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "exercício não encontrado")
    return exercicio, _modulo_visivel(sessao, exercicio.modulo_id, usuario)


def _apagar_exercicios(sessao: Session, ids: list[int]) -> None:
    if ids:
        sessao.exec(delete(Resposta).where(Resposta.exercicio_id.in_(ids)))
        sessao.exec(delete(Exercicio).where(Exercicio.id.in_(ids)))


# ------------------------------------------------------------------ módulos
@router.post("/salas/{sala_id}/modulos", response_model=ModuloResumo, status_code=status.HTTP_201_CREATED)
def criar_modulo(sala_id: int, dados: ModuloEntrada, prof: Usuario = Depends(exigir_professor),
                 sessao: Session = Depends(get_session)):
    sala_visivel(sessao, sala_id, prof)
    modulo = Modulo(sala_id=sala_id, **dados.model_dump())
    sessao.add(modulo)
    sessao.commit()
    sessao.refresh(modulo)
    return ModuloResumo(id=modulo.id, titulo=modulo.titulo, ordem=modulo.ordem, n_exercicios=0)


@router.get("/salas/{sala_id}/modulos", response_model=list[ModuloResumo])
def listar_modulos(sala_id: int, usuario: Usuario = Depends(usuario_atual), sessao: Session = Depends(get_session)):
    sala_visivel(sessao, sala_id, usuario)
    modulos = sessao.exec(select(Modulo).where(Modulo.sala_id == sala_id).order_by(Modulo.ordem, Modulo.id)).all()
    saida = []
    for m in modulos:
        n_ex = sessao.exec(select(func.count()).select_from(Exercicio).where(Exercicio.modulo_id == m.id)).one()
        n_ac = None
        if usuario.perfil == Perfil.aluno:
            n_ac = sessao.exec(select(func.count(func.distinct(Resposta.exercicio_id)))
                               .join(Exercicio, Exercicio.id == Resposta.exercicio_id)
                               .where(Exercicio.modulo_id == m.id, Resposta.aluno_id == usuario.id,
                                      Resposta.correta)).one()
        saida.append(ModuloResumo(id=m.id, titulo=m.titulo, ordem=m.ordem, n_exercicios=n_ex, n_acertados=n_ac))
    return saida


@router.get("/modulos/{modulo_id}", response_model=ModuloDetalhe)
def ver_modulo(modulo_id: int, usuario: Usuario = Depends(usuario_atual), sessao: Session = Depends(get_session)):
    modulo = _modulo_visivel(sessao, modulo_id, usuario)
    exercicios = sessao.exec(select(Exercicio).where(Exercicio.modulo_id == modulo.id)
                             .order_by(Exercicio.ordem, Exercicio.id)).all()
    if usuario.perfil == Perfil.professor:
        lista = [ExercicioProfessor(**e.model_dump()) for e in exercicios]
    else:
        lista = []
        for e in exercicios:
            resp = sessao.exec(select(Resposta.correta).where(Resposta.exercicio_id == e.id,
                                                               Resposta.aluno_id == usuario.id)).all()
            lista.append(ExercicioAluno(id=e.id, enunciado=e.enunciado, alternativas=e.alternativas,
                                        pontos=e.pontos, ordem=e.ordem, ja_respondeu=bool(resp),
                                        ja_acertou=any(resp)))
    return ModuloDetalhe(id=modulo.id, sala_id=modulo.sala_id, titulo=modulo.titulo, conteudo=modulo.conteudo,
                         ordem=modulo.ordem, exercicios=lista)


@router.put("/modulos/{modulo_id}", response_model=ModuloResumo)
def editar_modulo(modulo_id: int, dados: ModuloEntrada, prof: Usuario = Depends(exigir_professor),
                  sessao: Session = Depends(get_session)):
    modulo = _modulo_do_professor(sessao, modulo_id, prof)
    for campo, valor in dados.model_dump().items():
        setattr(modulo, campo, valor)
    sessao.add(modulo)
    sessao.commit()
    n_ex = sessao.exec(select(func.count()).select_from(Exercicio).where(Exercicio.modulo_id == modulo.id)).one()
    return ModuloResumo(id=modulo.id, titulo=modulo.titulo, ordem=modulo.ordem, n_exercicios=n_ex)


@router.delete("/modulos/{modulo_id}", status_code=status.HTTP_204_NO_CONTENT)
def apagar_modulo(modulo_id: int, prof: Usuario = Depends(exigir_professor), sessao: Session = Depends(get_session)):
    modulo = _modulo_do_professor(sessao, modulo_id, prof)
    _apagar_exercicios(sessao, list(sessao.exec(select(Exercicio.id).where(Exercicio.modulo_id == modulo.id)).all()))
    sessao.delete(modulo)
    sessao.commit()


# ------------------------------------------------------------------ exercícios
@router.post("/modulos/{modulo_id}/exercicios", response_model=ExercicioProfessor,
             status_code=status.HTTP_201_CREATED)
def criar_exercicio(modulo_id: int, dados: ExercicioEntrada, prof: Usuario = Depends(exigir_professor),
                    sessao: Session = Depends(get_session)):
    modulo = _modulo_do_professor(sessao, modulo_id, prof)
    exercicio = Exercicio(modulo_id=modulo.id, **dados.model_dump())
    sessao.add(exercicio)
    sessao.commit()
    sessao.refresh(exercicio)
    return ExercicioProfessor(**exercicio.model_dump())


@router.put("/exercicios/{exercicio_id}", response_model=ExercicioProfessor)
def editar_exercicio(exercicio_id: int, dados: ExercicioEntrada, prof: Usuario = Depends(exigir_professor),
                     sessao: Session = Depends(get_session)):
    exercicio, _ = _exercicio_visivel(sessao, exercicio_id, prof)
    for campo, valor in dados.model_dump().items():
        setattr(exercicio, campo, valor)
    sessao.add(exercicio)
    sessao.commit()
    sessao.refresh(exercicio)
    return ExercicioProfessor(**exercicio.model_dump())


@router.delete("/exercicios/{exercicio_id}", status_code=status.HTTP_204_NO_CONTENT)
def apagar_exercicio(exercicio_id: int, prof: Usuario = Depends(exigir_professor),
                     sessao: Session = Depends(get_session)):
    exercicio, _ = _exercicio_visivel(sessao, exercicio_id, prof)
    _apagar_exercicios(sessao, [exercicio.id])
    sessao.commit()


@router.post("/exercicios/{exercicio_id}/responder", response_model=RespostaSaida)
def responder(exercicio_id: int, dados: RespostaEntrada, aluno: Usuario = Depends(exigir_aluno),
              sessao: Session = Depends(get_session)):
    exercicio, _ = _exercicio_visivel(sessao, exercicio_id, aluno)
    if dados.alternativa >= len(exercicio.alternativas):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "alternativa inexistente")
    anteriores = sessao.exec(select(func.count()).select_from(Resposta).where(
        Resposta.exercicio_id == exercicio.id, Resposta.aluno_id == aluno.id)).one()
    primeira = anteriores == 0
    correta = dados.alternativa == exercicio.indice_correta
    pontos = exercicio.pontos if (correta and primeira) else 0     # regra em gamificacao.py
    sessao.add(Resposta(exercicio_id=exercicio.id, aluno_id=aluno.id, alternativa=dados.alternativa,
                        correta=correta, pontos_ganhos=pontos))
    sessao.commit()
    return RespostaSaida(correta=correta, indice_correta=exercicio.indice_correta, explicacao=exercicio.explicacao,
                         pontos_ganhos=pontos, primeira_tentativa=primeira)
