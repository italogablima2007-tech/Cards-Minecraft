
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from database import Base, engine
import models

# ==================================================
# CONFIGURAÇÃO DA API
# ==================================================

app = FastAPI(title="Reinos & Batalhas API")


# ==================================================
# CRIAÇÃO DAS TABELAS
# ==================================================

Base.metadata.create_all(bind=engine)


# ==================================================
# ROTA PRINCIPAL
# ==================================================

@app.get("/")
def inicio():
    return {
        "jogo": "Reinos & Batalhas",
        "status": "Servidor configurado"
    }


# ==================================================
# VERIFICAR SERVIDOR
# ==================================================

@app.get("/health")
def verificar_servidor():
    return {"status": "online"}


# ==================================================
# TESTAR POSTGRESQL
# ==================================================

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


# ==================================================
# VERIFICAR TABELAS DO BANCO
# ==================================================

from sqlalchemy import inspect


@app.get("/database-tables")
def verificar_tabelas():
    inspector = inspect(engine)

    tabelas = inspector.get_table_names()

    return {
        "banco": "PostgreSQL",
        "tabelas": tabelas,
        "jogadores_criada": "jogadores" in tabelas
    }

