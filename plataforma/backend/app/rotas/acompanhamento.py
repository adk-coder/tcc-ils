"""Acompanhamento: painel de desempenho da turma (professor) e "continuar de onde parou" (aluno).

Regras usadas no painel:
  - "acerto de primeira": a PRIMEIRA resposta de cada aluno em cada exercício (é a
    que mede o que o aluno sabia; depois ele já viu a correção). Mesma regra dos pontos.
  - "erro mais comum": a alternativa errada mais marcada nas primeiras respostas.
    Mostra ao professor QUAL confusão a turma está fazendo, não só que errou.
  - "concluíram": alunos que já acertaram (em qualquer tentativa) todos os exercícios do módulo.
Os dados ficam restritos à sala do professor (sala_visivel → 404 para quem não é dono).
"""

from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ..db import get_session
from ..deps import exigir_aluno, exigir_professor
from ..esquemas import (Continuar, DesempenhoAluno, DesempenhoExercicio, DesempenhoModulo, DesempenhoSala,
                        ErroComum)
from ..modelos import Exercicio, Matricula, Modulo, Resposta, Sala, Usuario
from .salas import sala_visivel

router = APIRouter(tags=["acompanhamento"])


def _resumo(texto: str, limite: int = 120) -> str:
    texto = " ".join(texto.split())
    return texto if len(texto) <= limite else texto[: limite - 1].rstrip() + "…"


@router.get("/salas/{sala_id}/desempenho", response_model=DesempenhoSala)
def desempenho_da_sala(sala_id: int, prof: Usuario = Depends(exigir_professor),
                       sessao: Session = Depends(get_session)):
    sala = sala_visivel(sessao, sala_id, prof)
    if sala.professor_id != prof.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "sala não encontrada")

    alunos = sessao.exec(select(Usuario).join(Matricula, Matricula.aluno_id == Usuario.id)
                         .where(Matricula.sala_id == sala.id).order_by(Usuario.nome)).all()
    ids_alunos = {a.id for a in alunos}
    modulos = sessao.exec(select(Modulo).where(Modulo.sala_id == sala.id).order_by(Modulo.ordem, Modulo.id)).all()
    exercicios = sessao.exec(select(Exercicio).where(Exercicio.modulo_id.in_([m.id for m in modulos]))
                             .order_by(Exercicio.ordem, Exercicio.id)).all() if modulos else []
    respostas = sessao.exec(select(Resposta).where(Resposta.exercicio_id.in_([e.id for e in exercicios]))
                            .order_by(Resposta.respondida_em, Resposta.id)).all() if exercicios else []
    # só quem ainda está na sala entra nas contas (aluno removido não distorce o painel)
    respostas = [r for r in respostas if r.aluno_id in ids_alunos]

    primeira: dict[tuple[int, int], Resposta] = {}      # (aluno, exercício) → 1ª resposta
    acertou: set[tuple[int, int]] = set()               # (aluno, exercício) acertado alguma vez
    for r in respostas:
        primeira.setdefault((r.aluno_id, r.exercicio_id), r)
        if r.correta:
            acertou.add((r.aluno_id, r.exercicio_id))

    saida_modulos, acertos_1a, total_1a = [], 0, 0
    for m in modulos:
        do_modulo = [e for e in exercicios if e.modulo_id == m.id]
        lista = []
        for n, e in enumerate(do_modulo, start=1):
            primeiras = [r for (a, ex), r in primeira.items() if ex == e.id]
            certas = sum(r.correta for r in primeiras)
            erradas = Counter(r.alternativa for r in primeiras if not r.correta)
            acertos_1a += certas
            total_1a += len(primeiras)
            lista.append(DesempenhoExercicio(
                id=e.id, numero=n, enunciado=_resumo(e.enunciado), responderam=len(primeiras),
                acerto_primeira=round(certas / len(primeiras), 4) if primeiras else None,
                erro_comum=ErroComum(alternativa=erradas.most_common(1)[0][0], quantos=erradas.most_common(1)[0][1])
                if erradas else None))
        concluiram = sum(all((a.id, e.id) in acertou for e in do_modulo) for a in alunos) if do_modulo else 0
        saida_modulos.append(DesempenhoModulo(id=m.id, titulo=m.titulo, concluiram=concluiram, exercicios=lista))

    saida_alunos = []
    for a in alunos:
        minhas = [r for r in respostas if r.aluno_id == a.id]
        saida_alunos.append(DesempenhoAluno(
            id=a.id, nome=a.nome, acertados=sum(1 for e in exercicios if (a.id, e.id) in acertou),
            pontos=sum(r.pontos_ganhos for r in minhas),
            ultima_atividade=max((r.respondida_em for r in minhas), default=None)))

    return DesempenhoSala(n_alunos=len(alunos), total_exercicios=len(exercicios),
                          acerto_primeira_medio=round(acertos_1a / total_1a, 4) if total_1a else None,
                          modulos=saida_modulos, alunos=saida_alunos)


@router.get("/eu/continuar", response_model=Continuar | None)
def continuar_de_onde_parou(aluno: Usuario = Depends(exigir_aluno), sessao: Session = Depends(get_session)):
    """Próximo módulo a estudar: o da última atividade, se ainda faltar algo; senão o próximo
    módulo da mesma sala; senão qualquer módulo com exercício por fazer. None = está em dia."""
    salas = sessao.exec(select(Sala).join(Matricula, Matricula.sala_id == Sala.id)
                        .where(Matricula.aluno_id == aluno.id).order_by(Sala.criada_em)).all()
    if not salas:
        return None
    nomes = {s.id: s.nome for s in salas}
    modulos = sessao.exec(select(Modulo).where(Modulo.sala_id.in_(list(nomes)))
                          .order_by(Modulo.ordem, Modulo.id)).all()
    modulos = sorted(modulos, key=lambda m: list(nomes).index(m.sala_id))     # agrupa por sala, mantém a ordem
    exercicios = sessao.exec(select(Exercicio).where(Exercicio.modulo_id.in_([m.id for m in modulos]))).all() \
        if modulos else []
    respostas = sessao.exec(select(Resposta).where(Resposta.aluno_id == aluno.id)
                            .order_by(Resposta.respondida_em.desc(), Resposta.id.desc())).all()
    acertados = {r.exercicio_id for r in respostas if r.correta}

    por_modulo = {m.id: [e.id for e in exercicios if e.modulo_id == m.id] for m in modulos}
    ex_para_modulo = {e.id: e.modulo_id for e in exercicios}

    candidatos = list(modulos)
    ultimo = next((ex_para_modulo[r.exercicio_id] for r in respostas if r.exercicio_id in ex_para_modulo), None)
    if ultimo is not None:
        i = next(k for k, m in enumerate(modulos) if m.id == ultimo)
        mesma_sala = [m for m in modulos[i:] if m.sala_id == modulos[i].sala_id]
        candidatos = mesma_sala + [m for m in modulos if m not in mesma_sala]

    for m in candidatos:
        ids = por_modulo[m.id]
        feitos = sum(e in acertados for e in ids)
        if ids and feitos < len(ids):
            return Continuar(sala_id=m.sala_id, sala_nome=nomes[m.sala_id], modulo_id=m.id,
                             modulo_titulo=m.titulo, feitos=feitos, total=len(ids))
    return None
