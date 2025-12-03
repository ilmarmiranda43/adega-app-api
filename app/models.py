# app/models.py
from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
    func,
    Computed,
)

from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone, timedelta
from .database import Base


# -----------------------------------------------------------
#  ADEGAS (TENANT)
# -----------------------------------------------------------
class Adega(Base):
    __tablename__ = "adegas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False)
    cnpj = Column(String(20), nullable=True)
    telefone = Column(String(20), nullable=True)
    email = Column(String(150), nullable=True)

    # Configuração de WhatsApp / TextMeBot (para o futuro)
    whatsapp_numero = Column(String(20), nullable=True)
    textmebot_api_key = Column(String(255), nullable=True)
    notificacao_ativa = Column(Boolean, default=False, nullable=False)

    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now(),nullable=False,)

    # Relações com outras entidades
    usuarios = relationship("Usuario",back_populates="adega",cascade="all, delete-orphan",)
    produtos = relationship("Produto",back_populates="adega",cascade="all, delete-orphan",)
    categorias = relationship("Categoria",back_populates="adega",cascade="all, delete-orphan",)
    clientes = relationship("Cliente",back_populates="adega",cascade="all, delete-orphan",)
    pedidos = relationship("Pedido",back_populates="adega",cascade="all, delete-orphan",)


# -----------------------------------------------------------
#  PRODUTOS
# -----------------------------------------------------------
class Produto(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    adega_id = Column(Integer, ForeignKey("adegas.id", ondelete="CASCADE"), nullable=False, index=True)
    categoria_id = Column(Integer, nullable=False, index=True)
    nome = Column(String(150), nullable=False)
    preco = Column(Numeric(10, 2), nullable=False)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now(),)

    __table_args__ = (
        ForeignKeyConstraint(
            ["adega_id", "categoria_id"],
            ["categorias.adega_id", "categorias.id"],
            name="produtos_categoria_fk",
            ondelete="RESTRICT",  # ou "CASCADE" se quiser apagar produtos ao apagar categoria
        ),
    )

    # relação com estoque
    adega = relationship("Adega", back_populates="produtos")
    categoria = relationship("Categoria", back_populates="produtos", overlaps="adega,produtos")
    estoques = relationship("Estoque", back_populates="produto")


# -----------------------------------------------------------
#  CATEGORIAS
# -----------------------------------------------------------
class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, index=True)
    adega_id = Column(Integer,ForeignKey("adegas.id", ondelete="CASCADE"),nullable=False,index=True,)

    # no banco está varchar(100), ajuste se quiser manter igual
    nome = Column(String(100), nullable=False)
    descricao = Column(String(255))

    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now(),)

    # Constraints extras (casam com o que fizemos no SQL)
    __table_args__ = (
        # necessário para a FK composta (adega_id, categoria_id) -> (adega_id, id)
        UniqueConstraint("adega_id", "id", name="categorias_adega_id_id_key"),
        # opcional, mas útil para impedir nome duplicado dentro da mesma adega
        UniqueConstraint("adega_id", "nome", name="categorias_adega_nome_key"),
    )

    # Relacionamentos ORM
    adega = relationship("Adega", back_populates="categorias")
    produtos = relationship("Produto", back_populates="categoria",overlaps="adega,produtos")


# -----------------------------------------------------------
#  PERFIS
# -----------------------------------------------------------
class Perfil(Base):
    __tablename__ = "perfis"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(50), unique=True, nullable=False)  # Admin, Gerente, Usuário
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

    # Multi-tenant: cada usuário pertence a UMA adega
    adega_id = Column(Integer, ForeignKey("adegas.id"), nullable=False, index=True)

    nome = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    senha_hash = Column(String, nullable=False)

    # perfil_id em vez de string
    perfil_id = Column(Integer, ForeignKey("perfis.id"), nullable=False)

    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    # relacionamentos ORM
    perfil = relationship("Perfil", back_populates="usuarios")
    adega = relationship("Adega", back_populates="usuarios")


# -----------------------------------------------------------
#  CLIENTES
# -----------------------------------------------------------
class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    adega_id = Column(Integer, ForeignKey("adegas.id"), nullable=False, index=True)
    nome = Column(String(150), nullable=False)
    email = Column(String(150), nullable=True, unique=True, index=True)
    telefone = Column(String(50), nullable=True)
    eh_whatsapp = Column(Boolean, default=True)
    observacoes = Column(String(500), nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now(),)

    # relacionamento com pedidos
    pedidos = relationship("Pedido", back_populates="cliente")
    adega = relationship("Adega", back_populates="clientes")


# -----------------------------------------------------------
#  ESTOQUE
# -----------------------------------------------------------
class Estoque(Base):
    __tablename__ = "estoque"

    id = Column(Integer, primary_key=True, index=True)

    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)

    quantidade = Column(Numeric(10, 2), nullable=False, default=0)
    minimo_alerta = Column(Numeric(10, 2), nullable=False, default=0)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime, nullable=True)
    
    produto = relationship("Produto", back_populates="estoques")


# -----------------------------------------------------------
#  PEDIDO
# -----------------------------------------------------------
class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    adega_id = Column(Integer,ForeignKey("adegas.id", ondelete="CASCADE"),nullable=False,index=True,)

    cliente_id = Column(Integer,ForeignKey("clientes.id", ondelete="CASCADE"),nullable=False,index=True,)

    
    status = Column(String(20), default="aberto")  # aberto, confirmado, cancelado
    
    observacoes = Column(String(500), nullable=True)
    valor_bruto = Column(Numeric(10, 2), default=0)
    desconto_total = Column(Numeric(10, 2), default=0)
    valor_liquido = Column(Numeric(10, 2), default=0)

    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    adega = relationship("Adega", back_populates="pedidos")
    cliente = relationship("Cliente", back_populates="pedidos")
    itens = relationship("ItemPedido",back_populates="pedido",cascade="all, delete-orphan")



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
    subtotal = Column(
        Numeric(10, 2),
        Computed("quantidade * preco_unitario"),
        nullable=False,
    )

    pedido = relationship("Pedido", back_populates="itens")
    produto = relationship("Produto")
