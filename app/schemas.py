from typing import Optional, List, Literal
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from datetime import datetime, date
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
# class PerfilBase(BaseModel):
#     adega_id: int
#     nome: str
#     descricao: Optional[str] = None


# class PerfilOut(PerfilBase):
#     id: int
#     ativo: bool
class PerfilBase(BaseModel):
    adega_id: int
    nome: str
    descricao: Optional[str] = None
    eh_admin: bool = False
    pode_gerenciar_usuarios: bool = False
    pode_gerenciar_estoque: bool = False
    pode_gerenciar_clientes: bool = False
    ativo: bool = True


class PerfilCreate(PerfilBase):
    pass


class PerfilUpdate(BaseModel):
    adega_id: Optional[int] = None
    nome: Optional[str] = None
    descricao: Optional[str] = None
    eh_admin: Optional[bool] = None
    pode_gerenciar_usuarios: Optional[bool] = None
    pode_gerenciar_estoque: Optional[bool] = None
    pode_gerenciar_clientes: Optional[bool] = None
    ativo: Optional[bool] = None


class PerfilOut(PerfilBase):
    id: int

    class Config:
        from_attributes = True

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
    adega_id: int | None = None
    adega_nome: str | None = None

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
    criado_em: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ---------- ITENS PEDIDO ----------
class ItemPedidoBase(BaseModel):
    produto_id: int
    quantidade: int = Field(..., gt=0)


class ItemPedidoCreate(ItemPedidoBase):
    # desconto opcional, padrão 0 – se o front não mandar nada,
    # você não quebra o NOT NULL do banco
    desconto: Decimal | None = Decimal("0.00")


class ItemPedidoRead(BaseModel):
    id: int
    produto_id: int
    quantidade: int
    preco_unitario: Decimal
    desconto: Decimal
    total_liquido: Decimal  # no lugar de subtotal

    class Config:
        from_attributes = True


class ItemPedidoResponse(BaseModel):
    id: int
    produto_id: int
    quantidade: int
    preco_unitario: Decimal
    desconto: Decimal
    total_liquido: Decimal

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
    usuario_id: int
    criado_em: datetime
    status: str
    observacoes: Optional[str]
    valor_liquido: Decimal
    itens: List[ItemPedidoRead]

    class Config:
        from_attributes = True


class PedidoResponse(BaseModel):
    id: int
    cliente_id: int
    status: str
    valor_liquido: Decimal
    observacoes: Optional[str]
    criado_em: Optional[datetime]
    itens: List[ItemPedidoResponse]

    class Config:
        from_attributes = True

# ====================================================================
#  USUÁRIOS
# ====================================================================

StatusDebito = Literal["aberto", "pago", "cancelado"]

class DebitoCreate(BaseModel):
    adega_id: int
    cliente_id: int
    valor: float = Field(..., ge=0)
    descricao: Optional[str] = None
    vencimento: Optional[date] = None

class DebitoOut(BaseModel):
    id: int
    adega_id: int
    cliente_id: int
    valor: float
    descricao: Optional[str]
    status: StatusDebito
    vencimento: Optional[date]
    criado_em: datetime
    whatsapp_enviado: bool

class EnviarWhatsAppIn(BaseModel):
    # opcional: se quiser personalizar a mensagem no front
    mensagem: Optional[str] = None


# ---------- PERFIL ----------


# class PerfilBase(BaseModel):
#     adega_id: int
#     nome: str
#     descricao: Optional[str] = None
#     eh_admin: bool = False
#     pode_gerenciar_usuarios: bool = False
#     pode_gerenciar_estoque: bool = False
#     pode_gerenciar_clientes: bool = False
#     ativo: bool = True


# class PerfilCreate(PerfilBase):
#     pass


# class PerfilUpdate(BaseModel):
#     adega_id: Optional[int] = None
#     nome: Optional[str] = None
#     descricao: Optional[str] = None
#     eh_admin: Optional[bool] = None
#     pode_gerenciar_usuarios: Optional[bool] = None
#     pode_gerenciar_estoque: Optional[bool] = None
#     pode_gerenciar_clientes: Optional[bool] = None
#     ativo: Optional[bool] = None


# class PerfilOut(PerfilBase):
#     id: int

#     class Config:
#         from_attributes = True
