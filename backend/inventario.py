
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from models import Inventario, Carta

router = APIRouter(
    prefix="/inventario",
    tags=["Inventário"]
)


@router.get("/me")
def meu_inventario(
    request: Request,
    db: Session = Depends(get_db)
):
    jogador_id = request.session.get("jogador_id")

    if not jogador_id:
        raise HTTPException(
            status_code=401,
            detail="Faça login com Discord"
        )

    registros = (
        db.query(Inventario, Carta)
        .join(Carta, Inventario.carta_id == Carta.id)
        .filter(Inventario.jogador_id == int(jogador_id))
        .all()
    )

    cartas = []

    for item, carta in registros:
        cartas.append({
            "inventario_id": item.id,
            "carta_id": carta.id,
            "firebase_id": carta.firebase_id,
            "nome": carta.nome,
            "raridade": carta.raridade,
            "classe": carta.classe,
            "reino_carta": carta.reino,
            "reino_inventario": item.reino,
            "quantidade": item.quantidade,
            "nivel": item.nivel,
            "xp": item.xp,
            "ultimo_treino": item.ultimo_treino,
            "imagem": carta.imagem
        })

    return {
        "jogador_id": jogador_id,
        "total": sum(item["quantidade"] or 0 for item in cartas),
        "cartas": cartas
    }
