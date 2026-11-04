"""Questionário adaptativo de estilos de aprendizagem (só para alunos).

Fluxo:  GET /eu/estilo  →  POST /eu/estilo/iniciar  →  POST /eu/estilo/responder (várias vezes)
Cada resposta devolve o novo estado: a próxima pergunta ou, quando o motor decide as
4 dimensões, o resultado. Quem escolhe a pergunta é sempre o servidor (app/ils/motor.py);
o aluno só pode responder a pergunta atual, o que evita respostas duplicadas (clique
duplo) e manipulação da ordem.
"""

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, delete, select

from ..db import get_session
from ..deps import exigir_aluno
from ..esquemas import DimensaoEstilo, EstadoEstilo, ItemRespondido, PerguntaEstilo, RespostaEstiloEntrada
from ..ils.motor import DIMENSOES, POLOS, MotorILS, dimensao_do_item
from ..ils.textos import texto_do_item, textos_provisorios
from ..modelos import QuestionarioEstilo, Usuario, agora

router = APIRouter(prefix="/eu/estilo", tags=["estilo de aprendizagem"])


@lru_cache
def _motor_do_arquivo() -> MotorILS:
    return MotorILS.de_arquivo()


def obter_motor() -> MotorILS:
    """Dependência: o modelo exportado de ia/ (lido do disco uma vez só)."""
    try:
        return _motor_do_arquivo()
    except FileNotFoundError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "o modelo do questionário ainda não foi exportado (rode ia/scripts/exportar_modelo.py)")


def _do_aluno(sessao: Session, aluno: Usuario) -> QuestionarioEstilo | None:
    return sessao.exec(select(QuestionarioEstilo).where(QuestionarioEstilo.aluno_id == aluno.id)).first()


def _resultado(decisao: dict) -> list[dict]:
    saida = []
    for d in decisao["dimensoes"]:
        a, b = POLOS[d["dimensao"]]
        polo_a = d["polo"] == 1
        saida.append({"dimensao": d["dimensao"], "polo": a if polo_a else b, "polo_oposto": b if polo_a else a,
                      "confianca": round(max(d["prob"], 1 - d["prob"]), 4), "n_questoes": d["n_questoes"]})
    return saida


def _estado(q: QuestionarioEstilo | None, motor: MotorILS) -> EstadoEstilo:
    provisorio = textos_provisorios()
    if q is None:
        return EstadoEstilo(status="nao_iniciado", textos_provisorios=provisorio)
    if q.concluido_em is not None:
        itens_resp = [
            ItemRespondido(
                numero=i + 1,
                item=item,
                dimensao=DIMENSOES[dimensao_do_item(item)],
                enunciado=texto_do_item(item)["enunciado"],
            )
            for i, (item, _) in enumerate(q.respostas)
        ]
        return EstadoEstilo(status="concluido", respondidas=len(q.respostas), partes_concluidas=4,
                            resultado=[DimensaoEstilo(**r) for r in q.resultado or []],
                            itens_respondidos=itens_resp,
                            concluido_em=q.concluido_em, textos_provisorios=provisorio)
    decisao = motor.proxima([(i, r) for i, r in q.respostas])
    texto = texto_do_item(decisao["item"])
    return EstadoEstilo(
        status="em_andamento", respondidas=len(q.respostas),
        partes_concluidas=sum(d["proximo"] is None for d in decisao["dimensoes"]),
        pergunta=PerguntaEstilo(item=decisao["item"], numero=len(q.respostas) + 1, enunciado=texto["enunciado"],
                                alternativa_a=texto["a"], alternativa_b=texto["b"]),
        textos_provisorios=provisorio)


@router.get("", response_model=EstadoEstilo)
def meu_estilo(aluno: Usuario = Depends(exigir_aluno), motor: MotorILS = Depends(obter_motor),
               sessao: Session = Depends(get_session)):
    return _estado(_do_aluno(sessao, aluno), motor)


@router.post("/iniciar", response_model=EstadoEstilo)
def iniciar(aluno: Usuario = Depends(exigir_aluno), motor: MotorILS = Depends(obter_motor),
            sessao: Session = Depends(get_session)):
    """Começa (ou recomeça do zero) o questionário. Um anterior é apagado."""
    sessao.exec(delete(QuestionarioEstilo).where(QuestionarioEstilo.aluno_id == aluno.id))
    q = QuestionarioEstilo(aluno_id=aluno.id, modelo=str(motor.info.get("experimento", "")))
    sessao.add(q)
    sessao.commit()
    sessao.refresh(q)
    return _estado(q, motor)


@router.post("/responder", response_model=EstadoEstilo)
def responder(dados: RespostaEstiloEntrada, aluno: Usuario = Depends(exigir_aluno),
              motor: MotorILS = Depends(obter_motor), sessao: Session = Depends(get_session)):
    q = _do_aluno(sessao, aluno)
    if q is None or q.concluido_em is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "nenhum questionário em andamento")
    atual = motor.proxima([(i, r) for i, r in q.respostas])["item"]
    if dados.item != atual:
        raise HTTPException(status.HTTP_409_CONFLICT, "esta não é a pergunta atual; recarregue a página")

    # lista NOVA (e não .append): assim o SQLAlchemy percebe que a coluna JSON mudou
    q.respostas = [*q.respostas, [dados.item, 1 if dados.resposta == "a" else 0]]
    decisao = motor.proxima([(i, r) for i, r in q.respostas])
    if decisao["item"] is None:                       # as 4 dimensões decididas
        q.resultado = _resultado(decisao)
        q.concluido_em = agora()
    sessao.add(q)
    sessao.commit()
    sessao.refresh(q)
    return _estado(q, motor)
