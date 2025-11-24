# app/models.py
from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Boolean,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


# -----------------------------------------------------------
#  PRODUTOS
# -----------------------------------------------------------
class Produto(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False)
    tipo_bebida = Column(String(60), nullable=False)
    marca = Column(String(80))
    volume_ml = Column(Integer)
    teor_alcoolico = Column(Numeric(5, 2))
    preco_custo = Column(Numeric(10, 2))
    preco_venda = Column(Numeric(10, 2), nullable=False)
    foto_url = Column(String)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())


# -----------------------------------------------------------
#  CATEGORIAS
# -----------------------------------------------------------
class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False, unique=True)
    descricao = Column(String(250))


# -----------------------------------------------------------
#  PERFIS
# -----------------------------------------------------------
class Perfil(Base):
    __tablename__ = "perfis"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(50), unique=True, nullable=False)
    descricao = Column(String(250))
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), server_default=func.now())

    usuarios = relationship("Usuario", back_populates="perfil")


# -----------------------------------------------------------
#  USUÁRIOS
# -----------------------------------------------------------
class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    senha_hash = Column(String, nullable=False)

    # Novo campo: perfil_id em vez de perfil string
    perfil_id = Column(Integer, ForeignKey("perfis.id"), nullable=False)

    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    # relacionamento ORM
    perfil = relationship("Perfil", back_populates="usuarios")
