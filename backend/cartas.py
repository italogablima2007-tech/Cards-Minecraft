
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
                "id": carta.id,
                "nome": carta.nome,
                "raridade": carta.raridade,
                "classe": carta.classe,
                "reino": carta.reino,
                "ataque": carta.ataque,
                "defesa": carta.defesa,
                "velocidade": carta.velocidade,
                "vida": carta.vida,
                "imagem": carta.imagem
            }
            for carta in cartas
        ]
    }
