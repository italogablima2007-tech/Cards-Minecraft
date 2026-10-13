
from fastapi import FastAPI

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
