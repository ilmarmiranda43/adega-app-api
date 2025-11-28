# app/schemas.py
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from datetime import datetime
from decimal import Decimal


# ====================================================================
#  PRODUTOS
# ====================================================================
class ProdutoBase(BaseModel):
    nome: str = Field(..., max_length=150)
    tipo_bebida: str = Field(..., max_length=60)
    marca: Optional[str] = Field(None, max_length=80)
    volume_ml: Optional[int] = None
    teor_alcoolico: Optional[float] = None
    preco_custo: Optional[float] = None
    preco_venda: float
    foto_url: Optional[str] = None
    ativo: Optional[bool] = True


class ProdutoCreate(ProdutoBase):
    pass


class ProdutoUpdate(BaseModel):
    nome: Optional[str] = None
    tipo_bebida: Optional[str] = None
    marca: Optional[str] = None
    volume_ml: Optional[int] = None
    teor_alcoolico: Optional[float] = None
    preco_custo: Optional[float] = None
    preco_venda: Optional[float] = None
    foto_url: Optional[str] = None
    ativo: Optional[bool] = None


class ProdutoOut(ProdutoBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ====================================================================
#  CATEGORIAS
# ====================================================================
class CategoriaBase(BaseModel):
    nome: str
    descricao: Optional[str] = None


class CategoriaCreate(CategoriaBase):
    pass


class CategoriaUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None


class CategoriaOut(CategoriaBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ====================================================================
#  PERFIS
# ====================================================================
class PerfilBase(BaseModel):
    nome: str
    descricao: Optional[str] = None


class PerfilOut(PerfilBase):
    id: int
    ativo: bool

    model_config = ConfigDict(from_attributes=True)


# ====================================================================
#  USUÁRIOS
# ====================================================================
class UsuarioBase(BaseModel):
    nome: str
    email: str
    perfil_id: int   # agora usa o ID do perfil


class UsuarioCreate(BaseModel):
    nome: str
    email: str
    senha: str = Field(..., min_length=6, max_length=72)
    perfil_id: int   # preenchido ao cadastrar usuário


class UsuarioOut(UsuarioBase):
    id: int
    perfil: Optional[PerfilOut] = None   # inclui nome + descricao do perfil

    model_config = ConfigDict(from_attributes=True)


# ====================================================================
#  LOGIN
# ====================================================================
class LoginRequest(BaseModel):
    email: str
    senha: str


class TokenData(BaseModel):
    user_id: int
    perfil_id: int


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UsuarioOut

# ---------- CLIENTES ----------

class ClienteBase(BaseModel):
    nome: str
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    # cidade: Optional[str] = None
    # estado: Optional[str] = None
    # cep: Optional[str] = None
    observacoes: Optional[str] = None


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    # cidade: Optional[str] = None
    # estado: Optional[str] = None
    # cep: Optional[str] = None
    observacoes: Optional[str] = None


class ClienteOut(ClienteBase):
    id: int
    criado_em: datetime
    atualizado_em: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ---------- ESTOQUE ----------

class EstoqueBase(BaseModel):
    produto_id: int
    quantidade: float
    local: Optional[str] = None
    data_entrada: Optional[datetime] = None
    data_validade: Optional[datetime] = None
    observacoes: Optional[str] = None


class EstoqueCreate(EstoqueBase):
    pass


class EstoqueUpdate(BaseModel):
    quantidade: Optional[float] = None
    local: Optional[str] = None
    data_entrada: Optional[datetime] = None
    data_validade: Optional[datetime] = None
    observacoes: Optional[str] = None


class EstoqueOut(EstoqueBase):
    id: int
    data_entrada: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# ---------- ITENS PEDIDO ----------

class ItemPedidoBase(BaseModel):
    produto_id: int
    quantidade: int


class ItemPedidoCreate(ItemPedidoBase):
    pass


class ItemPedidoRead(BaseModel):
    id: int
    produto_id: int
    quantidade: int
    preco_unitario: Decimal
    subtotal: Decimal

    class Config:
        from_attributes = True

class ItemPedidoResponse(BaseModel):
    id: int
    produto_id: int
    quantidade: int
    preco_unitario: Decimal
    subtotal: Decimal

    class Config:
        from_attributes = True

# ---------- PEDIDO ----------

class PedidoBase(BaseModel):
    cliente_id: int
    observacoes: Optional[str] = None


class PedidoCreate(PedidoBase):
    itens: List[ItemPedidoCreate]


class PedidoRead(BaseModel):
    id: int
    cliente_id: int
    data_criacao: datetime
    status: str
    observacoes: Optional[str]
    valor_total: Decimal
    itens: List[ItemPedidoRead]

    class Config:
        from_attributes = True

class PedidoResponse(BaseModel):
    id: int
    cliente_id: int
    status: str
    valor_total: Decimal
    observacoes: Optional[str]
    criado_em: Optional[datetime]
    itens: List[ItemPedidoResponse]

    class Config:
        from_attributes = True