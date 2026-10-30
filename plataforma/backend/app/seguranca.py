"""Senhas e tokens.

SENHAS: PBKDF2-HMAC-SHA256 da biblioteca padrão do Python (hashlib), com sal
aleatório por usuário e 600.000 iterações. A senha nunca é guardada; guarda-se
"pbkdf2_sha256$iterações$sal$hash". Para conferir, refaz-se o cálculo com o
mesmo sal e compara-se em tempo constante (evita ataque por tempo de resposta).
Escolhido por não depender de biblioteca externa e ser fácil de explicar.

TOKENS: JWT assinado com HMAC-SHA256 (PyJWT). O token carrega o id do usuário
("sub"), o perfil e a validade ("exp"). Como é assinado com SEGREDO_JWT, o
servidor percebe qualquer alteração feita pelo cliente.
"""

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from .config import config

ITERACOES = 600_000
ALGORITMO_JWT = "HS256"


def gerar_hash(senha: str, iteracoes: int | None = None) -> str:
    iteracoes = iteracoes or ITERACOES
    sal = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode(), sal, iteracoes)
    return f"pbkdf2_sha256${iteracoes}${base64.b64encode(sal).decode()}${base64.b64encode(dk).decode()}"


def conferir_senha(senha: str, armazenado: str) -> bool:
    try:
        algoritmo, iteracoes, sal_b64, hash_b64 = armazenado.split("$")
    except ValueError:
        return False
    if algoritmo != "pbkdf2_sha256":
        return False
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode(), base64.b64decode(sal_b64), int(iteracoes))
    return hmac.compare_digest(dk, base64.b64decode(hash_b64))


def criar_token(usuario_id: int, perfil: str) -> str:
    agora = datetime.now(timezone.utc)
    dados = {"sub": str(usuario_id), "perfil": perfil, "iat": agora,
             "exp": agora + timedelta(minutes=config.minutos_token)}
    return jwt.encode(dados, config.segredo_jwt, algorithm=ALGORITMO_JWT)


def ler_token(token: str) -> dict:
    """Valida assinatura e validade. Levanta jwt.PyJWTError se inválido."""
    return jwt.decode(token, config.segredo_jwt, algorithms=[ALGORITMO_JWT])


def gerar_codigo_sala() -> str:
    """Código de convite de 6 caracteres, sem letras/números ambíguos (0/O, 1/I)."""
    alfabeto = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alfabeto) for _ in range(6))
