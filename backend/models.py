
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, JSON
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

# ==================================================
# CARTAS DO JOGO
# ==================================================

class Carta(Base):
    __tablename__ = "cartas"

    id = Column(Integer, primary_key=True, index=True)

    nome = Column(String(100), nullable=False)

    raridade = Column(String(30), nullable=False)

    classe = Column(String(50), nullable=True)

    reino = Column(String(50), nullable=True)

    ataque = Column(Integer, default=0)

    defesa = Column(Integer, default=0)

    velocidade = Column(Integer, default=0)

    vida = Column(Integer, default=0)

    imagem = Column(String(1000), nullable=True)

    # Identificador original da carta no Firebase
    firebase_id = Column(String(100), unique=True, nullable=True)

    # Imagem de fundo da carta
    fundo = Column(String(1000), nullable=True)

    # Habilidades e progressão
    ataques = Column(JSON, default=list)
    passivas = Column(JSON, default=list)
    evolucoes = Column(JSON, default=list)


# ==================================================
# INVENTÁRIO DOS JOGADORES
# ==================================================

class Inventario(Base):
    __tablename__ = "inventarios"

    id = Column(Integer, primary_key=True, index=True)

    jogador_id = Column(
        Integer,
        ForeignKey("jogadores.id"),
        nullable=False,
        index=True
    )

    carta_id = Column(
        Integer,
        ForeignKey("cartas.id"),
        nullable=False,
        index=True
    )

    nivel = Column(Integer, default=0)

    xp = Column(Integer, default=0)

    
    # Reino proprietário do inventário
    reino = Column(String(50), nullable=True, index=True)

    # Quantidade de cópias da carta
    quantidade = Column(Integer, default=1)

    # Horário do último treinamento (milissegundos)
    ultimo_treino = Column(Integer().with_variant(
        __import__("sqlalchemy").BigInteger, "postgresql"
    ), default=0)

    criado_em = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

