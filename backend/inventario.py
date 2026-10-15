from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from firebase_admin import firestore

from database import get_db
from models import Inventario, Carta
from firebase_permissoes import verificar_usuario_firebase

router = APIRouter(prefix="/inventario", tags=["Inventário"])


@router.get("/me")
def meu_inventario(request: Request, db: Session = Depends(get_db)):
    jogador_id = request.session.get("jogador_id")
    if not jogador_id:
        raise HTTPException(status_code=401, detail="Faça login com Discord")

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


@router.get("/reino/{reino}")
def consultar_inventario_reino(
    reino: str,
    usuario: dict = Depends(verificar_usuario_firebase)
):
    reinos_validos = {"Drakmor", "Solaris", "Aetheryon"}
    if reino not in reinos_validos:
        raise HTTPException(status_code=404, detail="Reino não encontrado")
    if not usuario["admin"] and usuario["reino"] != reino:
        raise HTTPException(status_code=403, detail="Você não pode acessar o inventário de outro reino")

    try:
        documento = firestore.client().collection("inventarios").document(reino).get()
    except Exception:
        raise HTTPException(status_code=503, detail="Não foi possível consultar o inventário no Firebase")

    if not documento.exists:
        return {"reino": reino, "total": 0, "cartas": []}

    dados = documento.to_dict() or {}
    cartas = dados.get("cartas", [])
    if not isinstance(cartas, list):
        raise HTTPException(status_code=500, detail="Formato inválido do inventário")
    return {"reino": reino, "total": len(cartas), "cartas": cartas}
