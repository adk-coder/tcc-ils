"""Configuração: endereço do banco vindo do Neon/Render."""

from app.config import normalizar_url_banco


def test_url_do_banco_ganha_o_driver_psycopg():
    neon = "postgresql://usuario:senha@ep-x.sa-east-1.aws.neon.tech/neondb?sslmode=require"
    assert normalizar_url_banco(neon) == "postgresql+psycopg://usuario:senha@ep-x.sa-east-1.aws.neon.tech/neondb?sslmode=require"
    assert normalizar_url_banco("postgres://u:s@h/db") == "postgresql+psycopg://u:s@h/db"
    assert normalizar_url_banco("postgresql+psycopg://u:s@h/db") == "postgresql+psycopg://u:s@h/db"   # já certo
    assert normalizar_url_banco("sqlite:///./dev.db") == "sqlite:///./dev.db"
