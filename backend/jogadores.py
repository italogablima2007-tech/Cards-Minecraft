
from sqlalchemy.orm import Session
from models import Jogador


def buscar_jogador_por_discord(
    db: Session,
    discord_id: str
):
    return (
        db.query(Jogador)
        .filter(Jogador.discord_id == discord_id)
        .first()
    )


def criar_jogador(
    db: Session,
    discord_id: str,
    nome: str
):
    jogador = Jogador(
        discord_id=discord_id,
        nome=nome,
        reino=None
    )

    db.add(jogador)
    db.commit()
    db.refresh(jogador)

    return jogador
