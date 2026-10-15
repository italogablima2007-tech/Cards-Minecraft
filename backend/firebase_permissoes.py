
import os
import json

import firebase_admin
from firebase_admin import credentials, auth
from fastapi import Header, HTTPException


REINOS_UID = {
    "o4TMyQzGeqT5XEclTRK5rA8tDOF2": "Drakmor",
    "uwdUM1mMYEcMBKhC6XpNLrszAeI2": "Solaris",
    "GMJajxBKyoZkJGDKfCcHzLmwrGl2": "Aetheryon"
}


def inicializar_firebase():
    if firebase_admin._apps:
        return

    credenciais_json = os.getenv(
        "FIREBASE_CREDENTIALS_JSON"
    )

    if not credenciais_json:
        raise HTTPException(
            status_code=503,
            detail="Firebase não configurado"
        )

    try:
        credenciais = json.loads(credenciais_json)

        firebase_admin.initialize_app(
            credentials.Certificate(credenciais)
        )

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Erro ao inicializar Firebase"
        )


def verificar_usuario_firebase(
    authorization: str = Header(default=None)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Token Firebase obrigatório"
        )

    token = authorization.split(" ", 1)[1].strip()

    inicializar_firebase()

    try:
        usuario = auth.verify_id_token(token)

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Token Firebase inválido ou expirado"
        )

    uid = usuario.get("uid")

    admin_uid = os.getenv("FIREBASE_ADMIN_UID")

    if admin_uid and uid == admin_uid:
        return {
            "uid": uid,
            "admin": True,
            "reino": None
        }

    reino = REINOS_UID.get(uid)

    if not reino:
        raise HTTPException(
            status_code=403,
            detail="Conta sem permissão para acessar inventários"
        )

    return {
        "uid": uid,
        "admin": False,
        "reino": reino
    }
