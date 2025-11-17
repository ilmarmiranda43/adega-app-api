# app/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Pega a URL do banco do ambiente (Render ou .env local)
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    # Para testes locais, você pode colocar algo fixo aqui,
    # mas o ideal é usar variável de ambiente.
    # Exemplo local:
    # DATABASE_URL = "postgresql://usuario:senha@localhost:5432/adega"
    raise RuntimeError("DATABASE_URL não definida nas variáveis de ambiente")

# Render geralmente dá URL começando com postgres://
# SQLAlchemy prefere postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependência do FastAPI para injetar sessão do banco."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
