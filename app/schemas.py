from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from datetime import datetime
from decimal import Decimal


# ====================================================================
#  ADEGAS (TENANT)
# ====================================================================
class AdegaBase(BaseModel):
    nome: str
    cnpj: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[EmailStr] = None
    whatsapp_numero: Optional[str] = None
    textmebot_api_key: Optional[str] = None
    notificacao_ativa: bool = False  


class AdegaCreate(AdegaBase):
    pass


class AdegaUpdate(BaseModel):
    nome: Optional[str] = None
    cnpj: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[EmailStr] = None
    whatsapp_numero: Optional[str] = None
    textmebot_api_key: Optional[str] = None
    notificacao_ativa: bool = False  


class AdegaOut(AdegaBase):
    id: int
    notificacao_ativa: bool
    criado_em: datetime
    atualizado_em: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ====================================================================
#  PRODUTOS
#  (ajustado para o novo modelo: categoria_id + preco)
# ====================================================================
class ProdutoBase(BaseModel):
    adega_id: int
    nome: str = Field(..., max_length=150)
    categoria_id: int                  
    preco: Decimal                     
    ativo: bool = True                 


class ProdutoCreate(ProdutoBase):
    pass


class ProdutoUpdate(BaseModel):
    adega_id: int
    nome: Optional[str] = Field(None, max_length=150)
    categoria_id: Optional[int] = None
    preco: Optional[Decimal] = None
    ativo: Optional[bool] = None


class ProdutoOut(ProdutoBase):
    id: int
    criado_em: datetime
    atualizado_em: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ====================================================================
#  CATEGORIAS
# ====================================================================
class CategoriaBase(BaseModel):
    adega_id: int
    nome: str
    descricao: Optional[str] = None


class CategoriaCreate(CategoriaBase):
    pass


class CategoriaUpdate(BaseModel):
    adega_id: int
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
    email: EmailStr
    perfil_id: int          # ID do perfil (Admin, Gerente, Usuário)
    adega_id: int           # Multi-tenant: a qual adega o usuário pertence


class UsuarioCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str = Field(..., min_length=6, max_length=72)
    perfil_id: int
    adega_id: int


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
    adega_id: int   # agora o token também carrega a adega


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UsuarioOut


# ---------- CLIENTES ----------
class ClienteBase(BaseModel):
    adega_id: int
    nome: str
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    eh_whatsapp: bool
    observacoes: Optional[str] = None


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    adega_id: int
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    eh_whatsapp: bool
    observacoes: Optional[str] = None


class ClienteOut(ClienteBase):
    id: int
    criado_em: datetime
    atualizado_em: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ---------- ESTOQUE ----------
class EstoqueBase(BaseModel):
    adega_id: int
    produto_id: int
    quantidade: float
    minimo_alerta: int
    criado_em: Optional[datetime] = None
    

class EstoqueCreate(EstoqueBase):
    pass


class EstoqueUpdate(BaseModel):
    adega_id: int
    produto_id: int
    quantidade: float
    minimo_alerta: int
    criado_em: Optional[datetime] = None
    

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
