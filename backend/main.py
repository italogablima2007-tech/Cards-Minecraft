
# ==================================================
# CRIAÇÃO DAS TABELAS DO BANCO DE DADOS
# ==================================================

from database import Base, engine
import models

Base.metadata.create_all(bind=engine)
