
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from firebase_admin import firestore
from pydantic import BaseModel, Field
from collections import Counter
from datetime import datetime, timedelta, timezone
import secrets
import unicodedata

from database import get_db
from models import Inventario, Carta, ExclusaoCarta
from firebase_permissoes import (
    verificar_usuario_firebase,
    inicializar_firebase
)


router = APIRouter(
    prefix="/inventario",
    tags=["Inventário"]
)


REINOS_VALIDOS = {
    "Drakmor",
    "Solaris",
    "Aetheryon"
}


# ==========================================
# MODELO DE CONCESSÃO ADMINISTRATIVA
# ==========================================

class ConcessaoCartas(BaseModel):
    reino: str
    cartas: list[str] = Field(
        min_length=1,
        max_length=30
    )


# ==========================================
# INVENTÁRIO DO JOGADOR (DISCORD)
# ==========================================

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
        .filter(
            Inventario.jogador_id == int(jogador_id)
        )
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
        "total": sum(
            item["quantidade"] or 0
            for item in cartas
        ),
        "cartas": cartas
    }


# ==========================================
# CONSULTAR INVENTÁRIO DO REINO
# ==========================================

@router.get("/reino/{reino}")
def consultar_inventario_reino(
    reino: str,
    usuario: dict = Depends(
        verificar_usuario_firebase
    )
):
    if reino not in REINOS_VALIDOS:
        raise HTTPException(
            status_code=404,
            detail="Reino não encontrado"
        )

    if (
        not usuario["admin"]
        and usuario["reino"] != reino
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "Você não pode acessar o "
                "inventário de outro reino"
            )
        )

    try:
        inicializar_firebase()

        documento = (
            firestore.client()
            .collection("inventarios")
            .document(reino)
            .get()
        )

    except Exception:
        raise HTTPException(
            status_code=503,
            detail=(
                "Não foi possível consultar "
                "o inventário no Firebase"
            )
        )

    if not documento.exists:
        return {
            "reino": reino,
            "total": 0,
            "cartas": []
        }

    dados = documento.to_dict() or {}
    cartas = dados.get("cartas", [])

    if not isinstance(cartas, list):
        raise HTTPException(
            status_code=500,
            detail="Formato inválido do inventário"
        )

    return {
        "reino": reino,
        "total": len(cartas),
        "cartas": cartas
    }


# ==========================================
# ADICIONAR CARTAS - SOMENTE ADMIN
# ==========================================

@router.post("/admin/adicionar-cartas")
def adicionar_cartas_admin(
    dados: ConcessaoCartas,
    usuario: dict = Depends(
        verificar_usuario_firebase
    ),
    db: Session = Depends(get_db)
):
    # --------------------------------------
    # VERIFICAR ADMINISTRADOR
    # --------------------------------------

    if not usuario["admin"]:
        raise HTTPException(
            status_code=403,
            detail=(
                "Apenas o administrador "
                "pode conceder cartas."
            )
        )

    # --------------------------------------
    # VALIDAR REINO
    # --------------------------------------

    if dados.reino not in REINOS_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail="Reino inválido."
        )

    ids = [
        str(carta).strip()
        for carta in dados.cartas
    ]

    if any(not carta for carta in ids):
        raise HTTPException(
            status_code=400,
            detail="ID de carta inválido."
        )

    quantidades = Counter(ids)

    # --------------------------------------
    # VERIFICAR CATÁLOGO POSTGRESQL
    # --------------------------------------

    cartas_postgres = (
        db.query(Carta)
        .filter(
            Carta.firebase_id.in_(
                list(quantidades.keys())
            )
        )
        .all()
    )

    ids_encontrados = {
        str(carta.firebase_id)
        for carta in cartas_postgres
    }

    for carta_id in quantidades:
        if carta_id not in ids_encontrados:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Carta {carta_id} não "
                    "encontrada no PostgreSQL."
                )
            )

        exclusao = db.get(
            ExclusaoCarta,
            carta_id
        )

        if exclusao:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"A carta {carta_id} está "
                    "marcada para exclusão."
                )
            )

    # --------------------------------------
    # INICIALIZAR FIREBASE
    # --------------------------------------

    try:
        inicializar_firebase()
        banco = firestore.client()

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Firebase indisponível."
        )

    inventario_ref = (
        banco.collection("inventarios")
        .document(dados.reino)
    )

    # --------------------------------------
    # TRANSAÇÃO FIRESTORE
    # --------------------------------------

    @firestore.transactional
    def conceder(transacao):

        inventario_doc = inventario_ref.get(
            transaction=transacao
        )

        inventario = (
            inventario_doc.to_dict()
            if inventario_doc.exists
            else {}
        ) or {}

        lista = inventario.get(
            "cartas",
            []
        )

        if not isinstance(lista, list):
            raise ValueError(
                "Inventário inválido."
            )

        lista = [
            dict(carta)
            for carta in lista
        ]

        # ----------------------------------
        # VALIDAR CARTAS NO FIREBASE
        # ----------------------------------

        for carta_id in quantidades:

            carta_ref = (
                banco.collection("cartas")
                .document(carta_id)
            )

            exclusao_ref = (
                banco.collection("exclusoesCartas")
                .document(carta_id)
            )

            carta_doc = carta_ref.get(
                transaction=transacao
            )

            exclusao_doc = exclusao_ref.get(
                transaction=transacao
            )

            if exclusao_doc.exists:
                raise ValueError(
                    f"A carta {carta_id} "
                    "está excluída."
                )

            if not carta_doc.exists:
                raise ValueError(
                    f"A carta {carta_id} "
                    "não existe no Firebase."
                )

        # ----------------------------------
        # ATUALIZAR QUANTIDADES
        # ----------------------------------

        for carta_id, quantidade in (
            quantidades.items()
        ):

            existente = next(
                (
                    carta
                    for carta in lista
                    if str(
                        carta.get("idCarta")
                    ) == carta_id
                ),
                None
            )

            if existente:
                existente["quantidade"] = (
                    int(
                        existente.get(
                            "quantidade",
                            1
                        )
                    ) + quantidade
                )

            else:
                lista.append({
                    "idCarta": carta_id,
                    "quantidade": quantidade,
                    "nivel": 0,
                    "xp": 0
                })

        # ----------------------------------
        # LIMITE DO INVENTÁRIO
        # ----------------------------------

        if len(lista) > 500:
            raise ValueError(
                "O inventário ultrapassaria "
                "500 registros de cartas."
            )

        # ----------------------------------
        # SALVAR INVENTÁRIO
        # ----------------------------------

        transacao.set(
            inventario_ref,
            {"cartas": lista},
            merge=True
        )

        return sum(
            quantidades.values()
        )

    # ======================================
    # EXECUTAR TRANSAÇÃO
    # ======================================

    try:
        quantidade = conceder(
            banco.transaction()
        )

    except ValueError as erro:
        raise HTTPException(
            status_code=400,
            detail=str(erro)
        )

    except Exception:
        raise HTTPException(
            status_code=503,
            detail=(
                "Não foi possível concluir "
                "a concessão de cartas."
            )
        )

    return {
        "sucesso": True,
        "reino": dados.reino,
        "cartas_adicionadas": quantidade
    }

# ==========================================
# RESGATAR PACOTE PERSONALIZADO
# ==========================================

@router.post("/pacotes/{pacote_id}/resgatar")
def resgatar_pacote_backend(
    pacote_id: str,
    usuario: dict = Depends(verificar_usuario_firebase),
    db: Session = Depends(get_db)
):
    if not pacote_id or len(pacote_id) > 200 or "/" in pacote_id:
        raise HTTPException(status_code=400, detail="ID de pacote inválido.")

    inicializar_firebase()
    banco = firestore.client()
    pacote_ref = banco.collection("pacotesEnviados").document(pacote_id)

    @firestore.transactional
    def executar(transacao):
        pacote_doc = pacote_ref.get(transaction=transacao)
        if not pacote_doc.exists:
            raise HTTPException(status_code=404, detail="Pacote não encontrado.")

        pacote = pacote_doc.to_dict() or {}
        reino = pacote.get("destinatario")
        if reino not in REINOS_VALIDOS:
            raise HTTPException(status_code=400, detail="Destinatário inválido.")
        if not usuario["admin"] and usuario["reino"] != reino:
            raise HTTPException(status_code=403, detail="Este pacote pertence a outro reino.")
        if pacote.get("status") != "pendente":
            raise HTTPException(status_code=409, detail="Pacote não está pendente.")

        ids_originais = pacote.get("cartas")
        if (not isinstance(ids_originais, list)
                or not 1 <= len(ids_originais) <= 30):
            raise HTTPException(status_code=400, detail="Pacote inválido ou vazio.")

        ids = [str(item).strip() for item in ids_originais]
        if any(not item for item in ids):
            raise HTTPException(status_code=400, detail="Pacote contém ID inválido.")

        inventario_ref = banco.collection("inventarios").document(reino)
        inventario_doc = inventario_ref.get(transaction=transacao)
        dados_inventario = inventario_doc.to_dict() or {}
        lista_original = dados_inventario.get("cartas", [])
        if not isinstance(lista_original, list):
            raise HTTPException(status_code=409, detail="Inventário em formato inválido.")
        if any(not isinstance(item, dict) for item in lista_original):
            raise HTTPException(status_code=409, detail="Inventário contém registro inválido.")
        lista = [dict(item) for item in lista_original]

        # As leituras Firestore ocorrem antes das gravações.
        for carta_id in set(ids):
            carta_ref = banco.collection("cartas").document(carta_id)
            exclusao_ref = banco.collection("exclusoesCartas").document(carta_id)
            carta_doc = carta_ref.get(transaction=transacao)
            exclusao_doc = exclusao_ref.get(transaction=transacao)
            if exclusao_doc.exists or not carta_doc.exists:
                raise HTTPException(
                    status_code=409,
                    detail=f"Carta {carta_id} excluída ou indisponível."
                )

        # A marcação no PostgreSQL também é verificada, mas a
        # coordenação definitiva entre bancos ainda será implementada.
        ids_unicos = set(ids)
        cadastradas = db.query(Carta.firebase_id).filter(
            Carta.firebase_id.in_(ids_unicos)
        ).all()
        cadastradas_ids = {str(registro[0]) for registro in cadastradas}
        marcadas = db.query(ExclusaoCarta.firebase_id).filter(
            ExclusaoCarta.firebase_id.in_(ids_unicos)
        ).all()
        marcadas_ids = {str(registro[0]) for registro in marcadas}
        if ids_unicos - cadastradas_ids or marcadas_ids:
            raise HTTPException(
                status_code=409,
                detail="Pacote contém cartas ausentes ou marcadas para exclusão."
            )

        for carta_id in ids:
            existente = next(
                (item for item in lista if str(item.get("idCarta")) == carta_id),
                None
            )
            if existente is not None:
                existente["quantidade"] = int(existente.get("quantidade", 0)) + 1
            else:
                # Mantém o tipo original do ID (número/string), como no site.
                original = ids_originais[ids.index(carta_id)]
                lista.append({
                    "idCarta": original,
                    "quantidade": 1,
                    "nivel": 0,
                    "xp": 0
                })

        if len(lista) > 500:
            raise HTTPException(status_code=409, detail="Inventário excederia 500 cartas.")

        transacao.set(inventario_ref, {"cartas": lista}, merge=True)
        transacao.update(pacote_ref, {"status": "resgatado"})
        return {"sucesso": True, "reino": reino, "cartas": ids_originais,
                "pacote_id": pacote_id, "status": "resgatado"}

    try:
        return executar(banco.transaction())
    except HTTPException:
        raise
    except (ValueError, TypeError):
        raise HTTPException(status_code=409, detail="Dados inválidos no inventário.")
    except Exception:
        raise HTTPException(status_code=503, detail="Não foi possível resgatar o pacote.")

# ==========================================
# PACOTE DIÁRIO — SORTEIO E ENTREGA NO SERVIDOR
# ==========================================

CHANCES_DIARIAS = {
    "comum": 60,
    "rara": 25,
    "epica": 10,
    "lendaria": 4,
    "mitica": 1,
}
INTERVALO_DIARIO = timedelta(hours=24)


def _normalizar_raridade_diaria(valor):
    texto = unicodedata.normalize("NFD", str(valor or ""))
    return "".join(c for c in texto if unicodedata.category(c) != "Mn").lower().strip()


@router.post("/pacotes/diario/{reino}/abrir")
def abrir_pacote_diario_backend(
    reino: str,
    usuario: dict = Depends(verificar_usuario_firebase),
    db: Session = Depends(get_db),
):
    if reino not in REINOS_VALIDOS:
        raise HTTPException(status_code=404, detail="Reino não encontrado.")
    if usuario["admin"] or usuario["reino"] != reino:
        raise HTTPException(status_code=403, detail="Somente a conta do próprio reino pode abrir o pacote diário.")

    # O catálogo e a seleção são definidos exclusivamente no servidor.
    cartas_pg = db.query(Carta.firebase_id, Carta.raridade).filter(
        Carta.firebase_id.isnot(None)
    ).all()
    ids_catalogo = [str(registro[0]) for registro in cartas_pg if registro[0]]
    marcadas = set()
    if ids_catalogo:
        marcadas = {
            str(registro[0]) for registro in db.query(ExclusaoCarta.firebase_id).filter(
                ExclusaoCarta.firebase_id.in_(ids_catalogo)
            ).all()
        }
    grupos = {raridade: [] for raridade in CHANCES_DIARIAS}
    for firebase_id, raridade in cartas_pg:
        id_carta = str(firebase_id or "").strip()
        categoria = _normalizar_raridade_diaria(raridade)
        if id_carta and id_carta not in marcadas and categoria in grupos:
            grupos[categoria].append(id_carta)

    disponiveis = [(raridade, peso) for raridade, peso in CHANCES_DIARIAS.items() if grupos[raridade]]
    if not disponiveis:
        raise HTTPException(status_code=409, detail="Nenhuma carta válida disponível para o pacote diário.")

    try:
        inicializar_firebase()
        banco = firestore.client()
    except Exception:
        raise HTTPException(status_code=503, detail="Firebase indisponível.")

    diario_ref = banco.collection("pacotesDiarios").document(reino)
    inventario_ref = banco.collection("inventarios").document(reino)

    @firestore.transactional
    def executar(transacao):
        diario_doc = diario_ref.get(transaction=transacao)
        inventario_doc = inventario_ref.get(transaction=transacao)
        ultimo = (diario_doc.to_dict() or {}).get("abertoEm") if diario_doc.exists else None
        agora = datetime.now(timezone.utc)
        if ultimo is not None:
            if not isinstance(ultimo, datetime):
                raise HTTPException(status_code=409, detail="Data do último pacote inválida.")
            if ultimo.tzinfo is None:
                ultimo = ultimo.replace(tzinfo=timezone.utc)
            if agora < ultimo + INTERVALO_DIARIO:
                raise HTTPException(status_code=409, detail="Pacote indisponível: aguarde 24 horas desde a última abertura.")

        inventario = inventario_doc.to_dict() or {}
        original = inventario.get("cartas", [])
        if not isinstance(original, list) or any(not isinstance(item, dict) for item in original):
            raise HTTPException(status_code=409, detail="Inventário inválido.")
        lista = [dict(item) for item in original]

        # Conferir TODAS as cartas elegíveis dentro da transação, antes do sorteio.
        # Não sorteia cartas ausentes ou marcadas para exclusão no Firestore.
        elegiveis = {raridade: [] for raridade in CHANCES_DIARIAS}
        for raridade, _ in disponiveis:
            for id_carta in grupos[raridade]:
                carta_doc = banco.collection("cartas").document(id_carta).get(transaction=transacao)
                exclusao_doc = banco.collection("exclusoesCartas").document(id_carta).get(transaction=transacao)
                if carta_doc.exists and not exclusao_doc.exists:
                    elegiveis[raridade].append(id_carta)

        pesos = [(raridade, peso) for raridade, peso in CHANCES_DIARIAS.items() if elegiveis[raridade]]
        if not pesos:
            raise HTTPException(status_code=409, detail="Não há cartas disponíveis no catálogo Firebase.")

        total_peso = sum(peso for _, peso in pesos)
        ids = []
        for _ in range(3):
            sorteio = secrets.randbelow(total_peso)
            for raridade, peso in pesos:
                if sorteio < peso:
                    ids.append(secrets.choice(elegiveis[raridade]))
                    break
                sorteio -= peso

        for id_carta in ids:
            item = next((c for c in lista if str(c.get("idCarta")) == id_carta), None)
            if item is not None:
                try:
                    atual = int(item.get("quantidade", 0))
                except (ValueError, TypeError):
                    raise HTTPException(status_code=409, detail="Quantidade inválida no inventário.")
                if atual < 0:
                    raise HTTPException(status_code=409, detail="Quantidade inválida no inventário.")
                item["quantidade"] = atual + 1
            else:
                lista.append({"idCarta": id_carta, "quantidade": 1, "nivel": 0, "xp": 0})

        if len(lista) > 500:
            raise HTTPException(status_code=409, detail="Inventário excederia 500 tipos de cartas.")

        # Inventário e cooldown são gravados atomicamente.
        transacao.set(inventario_ref, {"cartas": lista}, merge=True)
        transacao.set(diario_ref, {"abertoEm": firestore.SERVER_TIMESTAMP})
        return {"sucesso": True, "reino": reino, "cartas": ids}

    try:
        return executar(banco.transaction())
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Não foi possível abrir o pacote diário.")
