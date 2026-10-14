
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Carta

router = APIRouter(
    prefix="/cartas",
    tags=["Cartas"]
)


@router.get("")
def listar_cartas(db: Session = Depends(get_db)):
    cartas = db.query(Carta).order_by(Carta.id).all()

    return {
        "total": len(cartas),
        "cartas": [
            {
                # Identificadores
                "id": carta.id,
                "firebase_id": carta.firebase_id,

                # Informações básicas
                "nome": carta.nome,
                "raridade": carta.raridade,
                "classe": carta.classe,
                "reino": carta.reino,

                # Atributos
                "ataque": carta.ataque,
                "defesa": carta.defesa,
                "velocidade": carta.velocidade,
                "vida": carta.vida,

                # Imagens
                "imagem": carta.imagem,
                "fundo": carta.fundo,

                # Sistema de combate
                "ataques": carta.ataques or [],
                "passivas": carta.passivas or [],

                # Sistema de evolução
                "evolucoes": carta.evolucoes or []
            }
            for carta in cartas
        ]
    }
