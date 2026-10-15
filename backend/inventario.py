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
