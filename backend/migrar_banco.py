
from sqlalchemy import text
from database import engine

def migrar_banco():
    print("Iniciando migração do PostgreSQL...")

    with engine.begin() as conexao:
        conexao.execute(text("""
            ALTER TABLE cartas
                ADD COLUMN IF NOT EXISTS firebase_id VARCHAR(100),
                ADD COLUMN IF NOT EXISTS fundo VARCHAR(1000),
                ADD COLUMN IF NOT EXISTS ataques JSON,
                ADD COLUMN IF NOT EXISTS passivas JSON,
                ADD COLUMN IF NOT EXISTS evolucoes JSON
        """))

        conexao.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS
                ix_cartas_firebase_id
            ON cartas (firebase_id)
        """))

        conexao.execute(text("""
            ALTER TABLE inventarios
                ALTER COLUMN nivel SET DEFAULT 0
        """))

    print("Migração concluída com sucesso!")


if __name__ == "__main__":
    migrar_banco()
