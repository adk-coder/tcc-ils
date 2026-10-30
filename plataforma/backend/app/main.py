"""Ponto de entrada da API.

Rodar em desenvolvimento (na pasta plataforma/backend, com o ambiente ativado):
    uvicorn app.main:app --reload
Documentação interativa gerada pelo FastAPI: http://localhost:8000/docs
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import config
from .db import criar_tabelas
from .rotas import acompanhamento, auth, conteudo, estilo, gamificacao, salas


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    criar_tabelas()
    yield


app = FastAPI(title="Plataforma de matemática — TCC IFC Videira", version="0.1.0", lifespan=ciclo_de_vida)

# CORS: permite que o frontend (Nuxt, outra porta/domínio) chame a API pelo navegador
app.add_middleware(CORSMiddleware, allow_origins=list(config.origens_cors), allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

app.include_router(auth.router)
app.include_router(salas.router)
app.include_router(conteudo.router)
app.include_router(gamificacao.router)
app.include_router(estilo.router)
app.include_router(acompanhamento.router)


@app.get("/saude", tags=["infra"])
def saude():
    return {"status": "ok"}
