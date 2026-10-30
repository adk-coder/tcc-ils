"""Configuração dos testes: banco SQLite em memória, novo a cada teste."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app import seguranca
from app.db import get_session
from app.main import app


@pytest.fixture
def cliente(monkeypatch):
    # Menos iterações só nos testes (600 mil deixaria cada cadastro lento)
    monkeypatch.setattr(seguranca, "ITERACOES", 1_000)
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    from app import modelos  # noqa: F401
    SQLModel.metadata.create_all(engine)

    def sessao_teste():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = sessao_teste
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def registrar(cliente, nome, email, perfil, senha="senha-forte-123"):
    r = cliente.post("/auth/registrar", json={"nome": nome, "email": email, "senha": senha,
                                              "perfil": perfil, "aceite_termos": True})
    assert r.status_code == 201, r.text
    t = cliente.post("/auth/login", json={"email": email, "senha": senha}).json()["access_token"]
    return {"Authorization": f"Bearer {t}"}
