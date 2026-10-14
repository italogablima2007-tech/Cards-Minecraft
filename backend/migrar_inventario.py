
from sqlalchemy import text
from database import engine

print("Iniciando atualização do inventário...")

with engine.begin() as conexao:
    conexao.execute(text("""
        ALTER TABLE inventarios
        ADD COLUMN IF NOT EXISTS reino VARCHAR(50);
    """))

    conexao.execute(text("""
        ALTER TABLE inventarios
        ADD COLUMN IF NOT EXISTS quantidade INTEGER DEFAULT 1;
    """))

    conexao.execute(text("""
        ALTER TABLE inventarios
        ADD COLUMN IF NOT EXISTS ultimo_treino BIGINT DEFAULT 0;
    """))

    conexao.execute(text("""
        CREATE INDEX IF NOT EXISTS
        ix_inventarios_reino
        ON inventarios (reino);
    """))

print("Inventário atualizado com sucesso!")
