"""Salas PvP online para FastAPI + PostgreSQL.
Instalação: app.include_router(router) em main.py.
Dependências: sqlalchemy, psycopg2-binary (ou driver compatível já instalado).
"""
import os
import secrets
import string
from datetime import datetime, timezone, timedelta
from threading import Lock

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, String, Integer, DateTime, JSON, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv('DATABASE_URL', '')
if not DATABASE_URL:
    raise RuntimeError('DATABASE_URL não configurada no Render')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = 'postgresql://' + DATABASE_URL[len('postgres://'):]
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Session = sessionmaker(bind=engine)
Base = declarative_base()
router = APIRouter(prefix='/pvp', tags=['PvP'])
_lock = Lock()

TERRENOS = ['🌨️ Tundra Congelada', '🌲 Floresta Ancestral', '🏜️ Deserto Escaldante',
            '🌋 Vulcão', '🌊 Costa Tempestuosa', '🏛️ Ruínas Antigas',
            '🌑 Abismo', '⚔️ Campo de Batalha']

class Sala(Base):
    __tablename__ = 'pvp_salas'
    codigo = Column(String(8), primary_key=True)
    status = Column(String(20), nullable=False, default='aguardando')
    jogador1 = Column(String(80), nullable=False)
    jogador2 = Column(String(80), nullable=True)
    token1 = Column(String(128), nullable=False)
    token2 = Column(String(128), nullable=True)
    escolha1 = Column(String(80), nullable=True)
    escolha2 = Column(String(80), nullable=True)
    pronto1 = Column(Integer, nullable=False, default=0)
    pronto2 = Column(Integer, nullable=False, default=0)
    terreno = Column(String(100), nullable=True)
    rodada = Column(Integer, nullable=False, default=0)
    time1 = Column(JSON, nullable=True)
    time2 = Column(JSON, nullable=True)
    convite_expira_em = Column(DateTime(timezone=True), nullable=True)
    escolha_expira_em = Column(DateTime(timezone=True), nullable=True)
    atualizado_em = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

Base.metadata.create_all(engine, tables=[Sala.__table__])
# Migração aditiva, sem apagar partidas já existentes.
with engine.begin() as con:
    for comando in [
        'ALTER TABLE pvp_salas ADD COLUMN IF NOT EXISTS time1 JSON',
        'ALTER TABLE pvp_salas ADD COLUMN IF NOT EXISTS time2 JSON',
        'ALTER TABLE pvp_salas ADD COLUMN IF NOT EXISTS convite_expira_em TIMESTAMPTZ',
        'ALTER TABLE pvp_salas ADD COLUMN IF NOT EXISTS escolha_expira_em TIMESTAMPTZ',
    ]:
        con.execute(text(comando))

class Jogador(BaseModel):
    nome: str = Field(min_length=1, max_length=50)
    time_ids: list[str] = Field(min_length=7, max_length=7)

def validar_time(ids):
    if len(ids) != 7 or len(set(ids)) != 7 or any(not str(x).strip() or len(str(x)) > 80 for x in ids):
        raise HTTPException(400, 'O time precisa ter exatamente 7 cartas diferentes')
    # TODO: validar cada ID no inventário autenticado, antes de permitir PvP competitivo.
    return list(ids)

def agora(): return datetime.now(timezone.utc)
def utc(data):
    if not data: return None
    return data.replace(tzinfo=timezone.utc) if data.tzinfo is None else data.astimezone(timezone.utc)

def atualizar_prazos(s):
    momento=agora()
    if s.status=='aguardando' and not s.jogador2 and s.convite_expira_em and momento>=utc(s.convite_expira_em):
        s.status='expirado'
    if s.status=='escolhendo' and s.escolha_expira_em and momento>=utc(s.escolha_expira_em):
        if not s.escolha1: s.escolha1=secrets.choice(s.time1)
        if not s.escolha2: s.escolha2=secrets.choice(s.time2)
        s.pronto1=s.pronto2=1
        iniciar(s)

def iniciar(s):
    s.status='em_andamento';s.rodada=1;s.terreno=secrets.choice(TERRENOS);s.atualizado_em=agora()


def cancelar_salas_com_carta(db, firebase_id):
    """
    Cancela salas de PvP que utilizam uma carta excluída.
    Deve ser chamada dentro da transação de exclusão.
    """
    carta_id = str(firebase_id)
    quantidade = 0

    salas = db.query(Sala).filter(
        Sala.status.in_([
            "aguardando",
            "escolhendo",
            "em_andamento"
        ])
    ).with_for_update().all()

    for sala in salas:
        time1 = [str(id) for id in (sala.time1 or [])]
        time2 = [str(id) for id in (sala.time2 or [])]

        if (
            carta_id in time1
            or carta_id in time2
            or str(sala.escolha1) == carta_id
            or str(sala.escolha2) == carta_id
        ):
            sala.status = "cancelado"
            sala.atualizado_em = agora()
            quantidade += 1

    return quantidade


class Escolha(BaseModel):
    carta_id: str = Field(min_length=1, max_length=80)

def obter(db, codigo, token):
    sala = db.get(Sala, codigo.upper())
    if not sala:
        raise HTTPException(404, 'Sala não encontrada')
    if not token or not secrets.compare_digest(token, sala.token1) and not (sala.token2 and secrets.compare_digest(token, sala.token2)):
        raise HTTPException(403, 'Acesso não autorizado à sala')
    return sala, 1 if secrets.compare_digest(token, sala.token1) else 2

def resumo(s, numero):
    # A escolha de cada jogador permanece privada até os dois confirmarem.
    mostrar = s.status == 'em_andamento'
    return {
        'codigo': s.codigo, 'status': s.status, 'voce': numero,
        'jogadores': [
            {'nome': s.jogador1, 'pronto': bool(s.pronto1), 'carta_id': s.escolha1 if mostrar or numero == 1 else None},
            {'nome': s.jogador2, 'pronto': bool(s.pronto2), 'carta_id': s.escolha2 if mostrar or numero == 2 else None}
        ],
        'terreno': s.terreno if mostrar else None,
        'rodada': s.rodada,
        'convite_expira_em': utc(s.convite_expira_em).isoformat() if s.convite_expira_em else None,
        'escolha_expira_em': utc(s.escolha_expira_em).isoformat() if s.escolha_expira_em else None,
        'time': s.time1 if numero == 1 else s.time2
    }

@router.post('/salas')
def criar_sala(jogador: Jogador):
    time_ids=validar_time(jogador.time_ids)
    token = secrets.token_urlsafe(32)
    with _lock, Session.begin() as db:
        for _ in range(20):
            codigo = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            if not db.get(Sala, codigo):
                db.add(Sala(codigo=codigo, jogador1=jogador.nome.strip(), token1=token, time1=time_ids, convite_expira_em=agora()+timedelta(seconds=30)))
                return {'codigo': codigo, 'token': token, 'jogador': 1}
    raise HTTPException(503, 'Não foi possível gerar o código')

@router.post('/salas/{codigo}/entrar')
def entrar(codigo: str, jogador: Jogador):
    time_ids=validar_time(jogador.time_ids)
    with _lock, Session.begin() as db:
        sala = db.get(Sala, codigo.upper(), with_for_update=True)
        if not sala:
            raise HTTPException(404, 'Sala não encontrada')
        atualizar_prazos(sala)
        if sala.jogador2:
            raise HTTPException(409, 'Sala cheia')
        if sala.status != 'aguardando':
            raise HTTPException(409, 'Convite expirado ou partida já iniciada')
        token = secrets.token_urlsafe(32)
        sala.jogador2 = jogador.nome.strip()
        sala.token2 = token
        sala.time2 = time_ids
        sala.status = 'escolhendo'
        sala.escolha_expira_em = agora() + timedelta(seconds=30)
        return {'codigo': sala.codigo, 'token': token, 'jogador': 2}

@router.get('/salas/{codigo}')
def consultar(codigo: str, x_pvp_token: str = Header(default='')):
    with Session.begin() as db:
        sala, n = obter(db, codigo, x_pvp_token)
        atualizar_prazos(sala)
        return resumo(sala, n)

@router.post('/salas/{codigo}/escolher')
def escolher(codigo: str, escolha: Escolha, x_pvp_token: str = Header(default='')):
    with Session.begin() as db:
        sala, n = obter(db, codigo, x_pvp_token)
        atualizar_prazos(sala)
        if sala.status != 'escolhendo':
            raise HTTPException(409, 'Fase de escolha encerrada')
        if (sala.pronto1 if n == 1 else sala.pronto2):
            raise HTTPException(409, 'Sua escolha já foi confirmada')
        time_ids = sala.time1 if n == 1 else sala.time2
        if escolha.carta_id not in time_ids:
            raise HTTPException(400, 'Escolha uma carta do seu time de 7')
        if n == 1:
            sala.escolha1 = escolha.carta_id
        else:
            sala.escolha2 = escolha.carta_id
        return resumo(sala, n)

@router.post('/salas/{codigo}/pronto')
def pronto(codigo: str, x_pvp_token: str = Header(default='')):
    with Session.begin() as db:
        sala, n = obter(db, codigo, x_pvp_token)
        atualizar_prazos(sala)
        if sala.status != 'escolhendo':
            raise HTTPException(409, 'Fase de escolha encerrada')
        if n == 1:
            if not sala.escolha1: raise HTTPException(400, 'Escolha sua carta inicial')
            sala.pronto1 = 1
        else:
            if not sala.escolha2: raise HTTPException(400, 'Escolha sua carta inicial')
            sala.pronto2 = 1
        if sala.jogador2 and sala.pronto1 and sala.pronto2:
            iniciar(sala)
        sala.atualizado_em = datetime.now(timezone.utc)
        return resumo(sala, n)

# =============================================================
# ETAPA 1 — ESTADO INICIAL DA ARENA ONLINE
# Cole este bloco NO FINAL de backend/pvp.py.
# Não apague as rotas existentes.
# =============================================================

@router.get('/salas/{codigo}/arena')
def consultar_arena(codigo: str, x_pvp_token: str = Header(default='')):
    """Entrega o estado inicial compartilhado da arena.

    Os IDs das cartas só são revelados após os dois jogadores
    confirmarem suas escolhas. Ainda não executa ataques.
    """
    with Session.begin() as db:
        sala, numero = obter(db, codigo, x_pvp_token)
        atualizar_prazos(sala)

        if sala.status != 'em_andamento':
            raise HTTPException(
                status_code=409,
                detail='A batalha ainda não começou. Aguarde os dois jogadores ficarem prontos.'
            )

        # O campo inicial tem quatro posições por jogador.
        # Somente a primeira posição está ocupada na rodada 1.
        return {
            'codigo': sala.codigo,
            'status': sala.status,
            'voce': numero,
            'rodada': sala.rodada,
            'terreno': sala.terreno,
            'jogadores': [
                {
                    'numero': 1,
                    'nome': sala.jogador1,
                    'campo': [sala.escolha1, None, None, None],
                    'time_ids': sala.time1 if numero == 1 else None,
                },
                {
                    'numero': 2,
                    'nome': sala.jogador2,
                    'campo': [sala.escolha2, None, None, None],
                    'time_ids': sala.time2 if numero == 2 else None,
                },
            ],
        }
