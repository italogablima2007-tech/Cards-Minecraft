
import json
from pathlib import Path

from sqlalchemy.orm import Session

from database import SessionLocal
from models import Carta


ARQUIVO = Path(__file__).parent / "cartas-reinos-batalhas.json"


def importar_cartas():
    if not ARQUIVO.exists():
        print(f"Arquivo não encontrado: {ARQUIVO}")
        return

    with ARQUIVO.open("r", encoding="utf-8") as arquivo:
        cartas = json.load(arquivo)

    if not isinstance(cartas, list):
        raise ValueError("O JSON deve conter uma lista de cartas.")

    ids = [str(carta["id"]) for carta in cartas]

    if len(ids) != len(set(ids)):
        raise ValueError("Existem IDs duplicados no arquivo.")

    banco: Session = SessionLocal()

    adicionadas = 0
    existentes = 0

    try:
        for dados in cartas:
            firebase_id = str(dados["id"])

            carta_existente = (
                banco.query(Carta)
                .filter(Carta.firebase_id == firebase_id)
                .first()
            )

            if carta_existente:
                existentes += 1
                continue

            carta = Carta(
                firebase_id=firebase_id,
                nome=dados["nome"],
                raridade=dados["raridade"],
                classe=dados.get("classe", ""),
                reino=dados.get("reino", ""),
                ataque=dados.get("ataque", 0),
                defesa=dados.get("defesa", 0),
                velocidade=dados.get("velocidade", 0),
                vida=dados.get("vida", 0),
                imagem=dados.get("imagem", ""),
                fundo=dados.get("fundo", ""),
                ataques=dados.get("ataques", []),
                passivas=dados.get("passivas", []),
                evolucoes=dados.get("evolucoes", []),
            )

            banco.add(carta)
            adicionadas += 1

        banco.commit()

        print("IMPORTAÇÃO CONCLUÍDA!")
        print(f"Cartas adicionadas: {adicionadas}")
        print(f"Cartas já existentes: {existentes}")
        print(f"Total processado: {len(cartas)}")

    except Exception:
        banco.rollback()
        raise

    finally:
        banco.close()


if __name__ == "__main__":
    importar_cartas()
