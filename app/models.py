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
from datetime import datetime, timezone, timedelta
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

    estoques = relationship("Estoque", back_populates="produto")


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


# -----------------------------------------------------------
#  CLIENTES
# -----------------------------------------------------------

class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False)
    email = Column(String(150), nullable=True, unique=True, index=True)
    telefone = Column(String(50), nullable=True)
    endereco = Column(String(255), nullable=True)
    # cidade = Column(String(120), nullable=True)
    # estado = Column(String(2), nullable=True)
    # cep = Column(String(20), nullable=True)
    observacoes = Column(String(500), nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow,nullable=False)

    # Se quiser ligar com pedidos no futuro, pode usar relationship aqui
    pedidos = relationship("Pedido", back_populates="cliente")


# -----------------------------------------------------------
#  ESTOQUE
# -----------------------------------------------------------
class Estoque(Base):
    __tablename__ = "estoque"

    id = Column(Integer, primary_key=True, index=True)

    # FK para produtos (ajuste o nome da tabela/coluna se for diferente na sua base)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)

    quantidade = Column(Numeric(10, 2), nullable=False, default=0)
    local = Column(String(120), nullable=True)
    data_entrada = Column(DateTime(timezone=True), server_default=func.now())
    data_validade = Column(DateTime, nullable=True)
    observacoes = Column(String(500), nullable=True)

    # relationships (ajuste o nome do modelo Produto)
    produto = relationship("Produto", back_populates="estoques")


# -----------------------------------------------------------
#  PEDIDO
# -----------------------------------------------------------

class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    data_criacao = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="aberto")  # aberto, confirmado, cancelado
    observacoes = Column(String(500), nullable=True)
    valor_total = Column(Numeric(10, 2), default=0)

    cliente = relationship("Cliente", back_populates="pedidos")
    itens = relationship("ItemPedido", back_populates="pedido", cascade="all, delete-orphan")


# -----------------------------------------------------------
#  ITEM PEDIDO
# -----------------------------------------------------------

class ItemPedido(Base):
    __tablename__ = "itens_pedido"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    quantidade = Column(Integer, nullable=False)
    preco_unitario = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)

    pedido = relationship("Pedido", back_populates="itens")
    produto = relationship("Produto")