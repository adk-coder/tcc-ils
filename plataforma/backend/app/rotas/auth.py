"""Cadastro, login e dados da própria conta (inclui direitos do titular — LGPD art. 18)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, delete, select

from ..db import get_session
from ..deps import usuario_atual
from ..esquemas import LoginEntrada, RegistroEntrada, Token, UsuarioSaida
from ..modelos import Exercicio, Matricula, Modulo, Perfil, QuestionarioEstilo, Resposta, Sala, Usuario
from ..seguranca import conferir_senha, criar_token, gerar_hash

router = APIRouter(prefix="/auth", tags=["autenticação"])


@router.post("/registrar", response_model=UsuarioSaida, status_code=status.HTTP_201_CREATED)
def registrar(dados: RegistroEntrada, sessao: Session = Depends(get_session)):
    if sessao.exec(select(Usuario).where(Usuario.email == dados.email)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "e-mail já cadastrado")
    usuario = Usuario(nome=dados.nome.strip(), email=dados.email, senha_hash=gerar_hash(dados.senha),
                      perfil=dados.perfil, consentimento_em=datetime.now(timezone.utc))
    sessao.add(usuario)
    sessao.commit()
    sessao.refresh(usuario)
    return usuario


@router.post("/login", response_model=Token)
def login(dados: LoginEntrada, sessao: Session = Depends(get_session)):
    usuario = sessao.exec(select(Usuario).where(Usuario.email == dados.email)).first()
    # mesma mensagem para e-mail inexistente e senha errada: não revela quem tem conta
    if usuario is None or not conferir_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "e-mail ou senha incorretos")
    return Token(access_token=criar_token(usuario.id, usuario.perfil.value))


@router.get("/eu", response_model=UsuarioSaida)
def eu(usuario: Usuario = Depends(usuario_atual)):
    return usuario


@router.get("/eu/dados")
def exportar_meus_dados(usuario: Usuario = Depends(usuario_atual), sessao: Session = Depends(get_session)):
    """Acesso/portabilidade: devolve tudo o que o sistema guarda sobre o titular."""
    if usuario.perfil == Perfil.professor:
        salas = sessao.exec(select(Sala).where(Sala.professor_id == usuario.id)).all()
        vinculos = [{"sala": s.nome, "papel": "professor", "desde": s.criada_em} for s in salas]
    else:
        linhas = sessao.exec(select(Matricula, Sala).join(Sala, Sala.id == Matricula.sala_id)
                             .where(Matricula.aluno_id == usuario.id)).all()
        vinculos = [{"sala": s.nome, "papel": "aluno", "desde": m.entrou_em} for m, s in linhas]
    respostas = sessao.exec(select(Resposta).where(Resposta.aluno_id == usuario.id)
                            .order_by(Resposta.respondida_em)).all()
    estilo = sessao.exec(select(QuestionarioEstilo).where(QuestionarioEstilo.aluno_id == usuario.id)).first()
    return {"conta": UsuarioSaida.model_validate(usuario, from_attributes=True).model_dump(),
            "consentimento_em": usuario.consentimento_em, "salas": vinculos,
            "respostas": [{"exercicio_id": r.exercicio_id, "alternativa": r.alternativa, "correta": r.correta,
                           "pontos": r.pontos_ganhos, "em": r.respondida_em} for r in respostas],
            "estilo_de_aprendizagem": None if estilo is None else {
                "respostas": [{"item": i, "resposta": "a" if r else "b"} for i, r in estilo.respostas],
                "resultado": estilo.resultado, "iniciado_em": estilo.iniciado_em,
                "concluido_em": estilo.concluido_em}}


@router.delete("/eu", status_code=status.HTTP_204_NO_CONTENT)
def excluir_minha_conta(usuario: Usuario = Depends(usuario_atual), sessao: Session = Depends(get_session)):
    """Eliminação: apaga a conta, as respostas, o questionário de estilo e os vínculos. Professor: apaga também as salas dele."""
    salas = list(sessao.exec(select(Sala.id).where(Sala.professor_id == usuario.id)).all())
    if salas:  # professor: leva junto módulos, exercícios e as respostas dadas a eles
        modulos = list(sessao.exec(select(Modulo.id).where(Modulo.sala_id.in_(salas))).all())
        exercicios = list(sessao.exec(select(Exercicio.id).where(Exercicio.modulo_id.in_(modulos))).all()) \
            if modulos else []
        if exercicios:
            sessao.exec(delete(Resposta).where(Resposta.exercicio_id.in_(exercicios)))
            sessao.exec(delete(Exercicio).where(Exercicio.id.in_(exercicios)))
        if modulos:
            sessao.exec(delete(Modulo).where(Modulo.id.in_(modulos)))
        sessao.exec(delete(Matricula).where(Matricula.sala_id.in_(salas)))
        sessao.exec(delete(Sala).where(Sala.id.in_(salas)))
    sessao.exec(delete(QuestionarioEstilo).where(QuestionarioEstilo.aluno_id == usuario.id))
    sessao.exec(delete(Resposta).where(Resposta.aluno_id == usuario.id))
    sessao.exec(delete(Matricula).where(Matricula.aluno_id == usuario.id))
    sessao.delete(usuario)
    sessao.commit()
