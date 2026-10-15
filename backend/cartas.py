import os
import json

import firebase_admin
from firebase_admin import credentials, auth as firebase_auth

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from pydantic import BaseModel, Field
from typing import Any

from database import get_db
from models import Carta, ExclusaoCarta


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


# ==========================================
# MODELO DE ENTRADA DAS CARTAS
# ==========================================

class CartaEntrada(BaseModel):
    id: str
    nome: str
    raridade: str
    classe: str = ""
    reino: str = ""
    ataque: int = 0
    defesa: int = 0
    velocidade: int = 0
    vida: int = 0
    imagem: str = ""
    fundo: str = ""
    ataques: list[dict[str, Any]] = Field(default_factory=list)
    passivas: list[dict[str, Any]] = Field(default_factory=list)
    evolucoes: list[dict[str, Any]] = Field(default_factory=list)


# ==========================================
# SINCRONIZAR CARTAS
# ==========================================

@router.post("/sincronizar")
def sincronizar_carta(
    dados: CartaEntrada,
    db: Session = Depends(get_db),
    admin: dict = Depends(verificar_admin_firebase)
):
    firebase_id = str(dados.id).strip()

    if not firebase_id:
        raise HTTPException(
            status_code=400,
            detail="ID da carta inválido"
        )

    if not dados.nome.strip() or not dados.raridade.strip():
        raise HTTPException(
            status_code=400,
            detail="Nome e raridade são obrigatórios"
        )

    # ==========================================
    # PROTEÇÃO CONTRA CARTAS EM EXCLUSÃO
    # ==========================================

    exclusao = db.get(ExclusaoCarta, firebase_id)

    if exclusao:
        raise HTTPException(
            status_code=409,
            detail=(
                "Esta carta está marcada para exclusão "
                "e não pode ser cadastrada ou atualizada."
            )
        )

    # ==========================================
    # LOCALIZAR CARTA NO POSTGRESQL
    # ==========================================

    carta = db.query(Carta).filter(
        Carta.firebase_id == firebase_id
    ).first()

    nova = carta is None

    if nova:
        carta = Carta(firebase_id=firebase_id)
        db.add(carta)

    carta.nome = dados.nome.strip()
    carta.raridade = dados.raridade.strip()
    carta.classe = dados.classe
    carta.reino = dados.reino
    carta.ataque = dados.ataque
    carta.defesa = dados.defesa
    carta.velocidade = dados.velocidade
    carta.vida = dados.vida
    carta.imagem = dados.imagem
    carta.fundo = dados.fundo
    carta.ataques = dados.ataques
    carta.passivas = dados.passivas
    carta.evolucoes = dados.evolucoes

    try:
        db.commit()
        db.refresh(carta)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Conflito ao cadastrar a carta. Tente novamente."
        )

    return {
        "sucesso": True,
        "acao": "criada" if nova else "atualizada",
        "id": carta.id,
        "firebase_id": carta.firebase_id,
        "nome": carta.nome
    }


# ==========================================
# EXCLUSÃO ADMINISTRATIVA DE CARTAS
# ==========================================

@router.delete("/{firebase_id}")
def excluir_carta(
    firebase_id: str,
    db: Session = Depends(get_db),
    admin: dict = Depends(verificar_admin_firebase)
):
    firebase_id = firebase_id.strip()

    if not firebase_id:
        raise HTTPException(
            status_code=400,
            detail="ID da carta inválido"
        )

    # ==========================================
    # VERIFICAR SE A CARTA EXISTE
    # ==========================================

    carta = db.query(Carta).filter(
        Carta.firebase_id == firebase_id
    ).first()

    if not carta:
        raise HTTPException(
            status_code=404,
            detail="Carta não encontrada no PostgreSQL"
        )

    # ==========================================
    # VERIFICAR EXCLUSÃO EXISTENTE
    # ==========================================

    exclusao = db.get(ExclusaoCarta, firebase_id)

    if exclusao:
        raise HTTPException(
            status_code=409,
            detail="Já existe uma solicitação de exclusão para esta carta"
        )

    # ==========================================
    # REGISTRAR EXCLUSÃO PENDENTE
    # ==========================================

    exclusao = ExclusaoCarta(
        firebase_id=firebase_id,
        status="pendente"
    )

    try:
        db.add(exclusao)
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Esta exclusão já foi solicitada"
        )

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Não foi possível registrar a exclusão"
        )

    return {
        "sucesso": True,
        "exclusao_concluida": False,
        "firebase_id": firebase_id,
        "status": "pendente",
        "mensagem": (
            "Solicitação registrada. "
            "A carta ainda não foi excluída."
        )
    }
