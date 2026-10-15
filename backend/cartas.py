
import os
import json

import firebase_admin
from firebase_admin import credentials, auth as firebase_auth

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Carta


# ==========================================
# CONFIGURAÇÃO DAS ROTAS
# ==========================================

router = APIRouter(
    prefix="/cartas",
    tags=["Cartas"]
)


# ==========================================
# VERIFICAR ADMINISTRADOR FIREBASE
# ==========================================

def verificar_admin_firebase(
    authorization: str = Header(default=None)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Token de autenticação não informado"
        )

    token = authorization.split(" ", 1)[1].strip()

    try:
        if not firebase_admin._apps:
            credenciais_json = os.environ["FIREBASE_CREDENTIALS_JSON"]
            credenciais = json.loads(credenciais_json)

            firebase_admin.initialize_app(
                credentials.Certificate(credenciais)
            )

        usuario = firebase_auth.verify_id_token(token)

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Token Firebase inválido ou configuração incorreta"
        )

    admin_uid = os.environ.get("FIREBASE_ADMIN_UID")

    if not admin_uid:
        raise HTTPException(
            status_code=503,
            detail="Administrador não configurado no servidor"
        )

    if usuario.get("uid") != admin_uid:
        raise HTTPException(
            status_code=403,
            detail="Apenas o administrador pode modificar cartas"
        )

    return usuario


# ==========================================
# LISTAR CARTAS
# ==========================================

@router.get("")
def listar_cartas(db: Session = Depends(get_db)):
    cartas = db.query(Carta).order_by(Carta.id).all()

    return {
        "total": len(cartas),
        "cartas": [
            {
                "id": carta.id,
                "firebase_id": carta.firebase_id,

                "nome": carta.nome,
                "raridade": carta.raridade,
                "classe": carta.classe,
                "reino": carta.reino,

                "ataque": carta.ataque,
                "defesa": carta.defesa,
                "velocidade": carta.velocidade,
                "vida": carta.vida,

                "imagem": carta.imagem,
                "fundo": carta.fundo,

                "ataques": carta.ataques or [],
                "passivas": carta.passivas or [],
                "evolucoes": carta.evolucoes or []
            }
            for carta in cartas
        ]
    }
