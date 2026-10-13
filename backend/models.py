
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from database import Base


class Jogador(Base):
    __tablename__ = "jogadores"

    id = Column(Integer, primary_key=True, index=True)

    discord_id = Column(String(30), unique=True, index=True)

    nome = Column(String(100), nullable=False)

    reino = Column(String(50), nullable=True)

    criado_em = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
