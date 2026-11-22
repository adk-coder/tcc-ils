"""Salas virtuais.

Regras de acesso:
  - só professor cria sala, vê o código de convite e remove alunos;
  - aluno entra numa sala pelo código;
  - uma sala só é visível para o professor dono e para os alunos matriculados
    (os outros recebem 404, para não revelar que a sala existe).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from ..db import get_session
from ..deps import exigir_aluno, exigir_professor, usuario_atual
from ..esquemas import AlunoNaSala, DimensaoAgregada, EntrarSalaEntrada, PerfilTurma, SalaDetalhe, SalaEntrada, SalaSaida
from ..modelos import Matricula, Perfil, QuestionarioEstilo, Sala, Usuario
from ..seguranca import gerar_codigo_sala

router = APIRouter(prefix="/salas", tags=["salas"])

# Pares de polos por dimensão (fato do instrumento ILS, independente do modelo de IA).
_POLOS: dict[str, tuple[str, str]] = {
    "ati_ref": ("ativo", "reflexivo"),
    "sen_int": ("sensorial", "intuitivo"),
    "vis_ver": ("visual", "verbal"),
    "seq_glo": ("sequencial", "global"),
}
_ORDEM_DIMENSOES = ("ati_ref", "sen_int", "vis_ver", "seq_glo")
_MINIMO_PERFIL = 5


def _n_alunos(sessao: Session, sala_id: int) -> int:
    return sessao.exec(select(func.count()).select_from(Matricula).where(Matricula.sala_id == sala_id)).one()


def _saida(sessao: Session, sala: Sala, mostrar_codigo: bool) -> SalaSaida:
    return SalaSaida(id=sala.id, nome=sala.nome, codigo=sala.codigo if mostrar_codigo else "",
                     professor_id=sala.professor_id, criada_em=sala.criada_em,
                     n_alunos=_n_alunos(sessao, sala.id))


def sala_visivel(sessao: Session, sala_id: int, usuario: Usuario) -> Sala:
    sala = sessao.get(Sala, sala_id)
    if sala is not None:
        if sala.professor_id == usuario.id:
            return sala
        if usuario.perfil == Perfil.aluno and sessao.get(Matricula, (sala_id, usuario.id)):
            return sala
    raise HTTPException(status.HTTP_404_NOT_FOUND, "sala não encontrada")


@router.post("", response_model=SalaSaida, status_code=status.HTTP_201_CREATED)
def criar_sala(dados: SalaEntrada, prof: Usuario = Depends(exigir_professor),
               sessao: Session = Depends(get_session)):
    codigo = gerar_codigo_sala()
    while sessao.exec(select(Sala).where(Sala.codigo == codigo)).first():  # colisão é raríssima
        codigo = gerar_codigo_sala()
    sala = Sala(nome=dados.nome.strip(), codigo=codigo, professor_id=prof.id)
    sessao.add(sala)
    sessao.commit()
    sessao.refresh(sala)
    return _saida(sessao, sala, mostrar_codigo=True)


@router.get("", response_model=list[SalaSaida])
def minhas_salas(usuario: Usuario = Depends(usuario_atual), sessao: Session = Depends(get_session)):
    if usuario.perfil == Perfil.professor:
        salas = sessao.exec(select(Sala).where(Sala.professor_id == usuario.id).order_by(Sala.criada_em)).all()
        return [_saida(sessao, s, mostrar_codigo=True) for s in salas]
    salas = sessao.exec(select(Sala).join(Matricula, Matricula.sala_id == Sala.id)
                        .where(Matricula.aluno_id == usuario.id).order_by(Sala.criada_em)).all()
    return [_saida(sessao, s, mostrar_codigo=False) for s in salas]


@router.post("/entrar", response_model=SalaSaida)
def entrar_na_sala(dados: EntrarSalaEntrada, aluno: Usuario = Depends(exigir_aluno),
                   sessao: Session = Depends(get_session)):
    sala = sessao.exec(select(Sala).where(Sala.codigo == dados.codigo.strip().upper())).first()
    if sala is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "código de sala inválido")
    if not sessao.get(Matricula, (sala.id, aluno.id)):
        sessao.add(Matricula(sala_id=sala.id, aluno_id=aluno.id))
        sessao.commit()
    return _saida(sessao, sala, mostrar_codigo=False)


@router.get("/{sala_id}", response_model=SalaDetalhe)
def detalhe_sala(sala_id: int, usuario: Usuario = Depends(usuario_atual), sessao: Session = Depends(get_session)):
    sala = sala_visivel(sessao, sala_id, usuario)
    dono = sala.professor_id == usuario.id
    professor = sessao.get(Usuario, sala.professor_id)
    alunos = []
    if dono:  # LGPD: aluno não vê a lista de colegas; só o professor
        linhas = sessao.exec(select(Matricula, Usuario).join(Usuario, Usuario.id == Matricula.aluno_id)
                             .where(Matricula.sala_id == sala.id).order_by(Usuario.nome)).all()
        alunos = [AlunoNaSala(id=u.id, nome=u.nome, entrou_em=m.entrou_em) for m, u in linhas]
    base = _saida(sessao, sala, mostrar_codigo=dono)
    return SalaDetalhe(**base.model_dump(), professor_nome=professor.nome, alunos=alunos)


@router.delete("/{sala_id}/alunos/{aluno_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_aluno(sala_id: int, aluno_id: int, prof: Usuario = Depends(exigir_professor),
                  sessao: Session = Depends(get_session)):
    sala = sala_visivel(sessao, sala_id, prof)
    matricula = sessao.get(Matricula, (sala.id, aluno_id))
    if matricula is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "aluno não está nesta sala")
    sessao.delete(matricula)
    sessao.commit()


@router.delete("/{sala_id}/sair", status_code=status.HTTP_204_NO_CONTENT)
def sair_da_sala(sala_id: int, aluno: Usuario = Depends(exigir_aluno), sessao: Session = Depends(get_session)):
    matricula = sessao.get(Matricula, (sala_id, aluno.id))
    if matricula is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "sala não encontrada")
    sessao.delete(matricula)
    sessao.commit()


@router.get("/{sala_id}/perfil-turma", response_model=PerfilTurma)
def perfil_turma(sala_id: int, prof: Usuario = Depends(exigir_professor),
                 sessao: Session = Depends(get_session)):
    """Perfil agregado e anônimo dos estilos de aprendizagem da turma (só para o professor dono da sala)."""
    sala = sessao.get(Sala, sala_id)
    if sala is None or sala.professor_id != prof.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "acesso negado")

    questionarios = sessao.exec(
        select(QuestionarioEstilo)
        .join(Matricula, Matricula.aluno_id == QuestionarioEstilo.aluno_id)
        .where(Matricula.sala_id == sala_id)
        .where(QuestionarioEstilo.concluido_em.isnot(None))
    ).all()

    respondentes = len(questionarios)
    if respondentes < _MINIMO_PERFIL:
        return PerfilTurma(respondentes=respondentes, minimo_atingido=False)

    contagem: dict[str, dict[str, int]] = {d: {a: 0, b: 0} for d, (a, b) in _POLOS.items()}
    for q in questionarios:
        for r in (q.resultado or []):
            dim = r["dimensao"]
            polo = r["polo"]
            if dim in contagem and polo in contagem[dim]:
                contagem[dim][polo] += 1

    dimensoes = []
    for dim in _ORDEM_DIMENSOES:
        a, b = _POLOS[dim]
        total = contagem[dim][a] + contagem[dim][b]
        if total == 0:
            continue
        pct_a = round(contagem[dim][a] / total * 100, 1)
        dimensoes.append(DimensaoAgregada(
            dimensao=dim, polo_a=a, polo_b=b,
            percentual_a=pct_a, percentual_b=round(100.0 - pct_a, 1),
        ))

    return PerfilTurma(respondentes=respondentes, minimo_atingido=True, dimensoes=dimensoes)
