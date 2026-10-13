
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from database import engine

app = FastAPI(title="Reinos & Batalhas API")


@app.get("/")
def inicio():
    return {
        "jogo": "Reinos & Batalhas",
        "status": "Servidor configurado"
    }


@app.get("/health")
def verificar_servidor():
    return {"status": "online"}


@app.get("/database-test")
def testar_banco():
    try:
        with engine.connect() as conexao:
            conexao.execute(text("SELECT 1"))

        return {
            "banco": "PostgreSQL",
            "status": "conectado"
        }

    except SQLAlchemyError:
        return {
            "banco": "PostgreSQL",
            "status": "erro de conexao"
        }
