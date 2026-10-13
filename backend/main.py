
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
# SISTEMA DE INVENTÁRIO
# ==================================================

from inventario import router as inventario_router

app.include_router(inventario_router)


# ==================================================
# LOGIN COM DISCORD
# ==================================================

import os
from starlette.middleware.sessions import SessionMiddleware
from auth import router as discord_router

SESSION_SECRET = os.environ["SESSION_SECRET"]

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
    https_only=True
)

app.include_router(discord_router)


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


# ==================================================
# CONSULTAR JOGADORES CADASTRADOS
# ==================================================

from sqlalchemy.orm import Session
from fastapi import Depends
from database import get_db
from models import Jogador


@app.get("/jogadores")
def listar_jogadores(db: Session = Depends(get_db)):
    jogadores = db.query(Jogador).all()

    return {
        "total": len(jogadores),
        "jogadores": [
            {
                "id": jogador.id,
                "nome": jogador.nome,
                "reino": jogador.reino
            }
            for jogador in jogadores
        ]
    }
