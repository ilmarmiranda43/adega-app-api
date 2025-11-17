# app/models.py
from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Boolean,
    DateTime,
)
from sqlalchemy.sql import func

from .database import Base


class Produto(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False)
    tipo_bebida = Column(String(60), nullable=False)  # vinho, cerveja, destilado...
    marca = Column(String(80))
    volume_ml = Column(Integer)
    teor_alcoolico = Column(Numeric(5, 2))
    preco_custo = Column(Numeric(10, 2))
    preco_venda = Column(Numeric(10, 2), nullable=False)
    foto_url = Column(String)  # armazena só a URL da imagem
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False, unique=True)
    descricao = Column(String(250))