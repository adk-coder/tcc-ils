"""Dependências do FastAPI para autenticação e autorização.

Uso numa rota:
    def minha_rota(usuario: Usuario = Depends(usuario_atual)): ...
    def so_professor(prof: Usuario = Depends(exigir_professor)): ...
O cliente envia o cabeçalho  Authorization: Bearer <token>.
"""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from .db import get_session
from .modelos import Perfil, Usuario
from .seguranca import ler_token

_bearer = HTTPBearer(auto_error=False)


def usuario_atual(cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
                  sessao: Session = Depends(get_session)) -> Usuario:
    nao_autorizado = HTTPException(status.HTTP_401_UNAUTHORIZED, "não autenticado",
                                   headers={"WWW-Authenticate": "Bearer"})
    if cred is None:
        raise nao_autorizado
    try:
        dados = ler_token(cred.credentials)
    except jwt.PyJWTError:
        raise nao_autorizado
    usuario = sessao.get(Usuario, int(dados["sub"]))
    if usuario is None:  # conta excluída depois de o token ser emitido
        raise nao_autorizado
    return usuario


def exigir_professor(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
    if usuario.perfil != Perfil.professor:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "apenas professores")
    return usuario


def exigir_aluno(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
    if usuario.perfil != Perfil.aluno:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "apenas alunos")
    return usuario
