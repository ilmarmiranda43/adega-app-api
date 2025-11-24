# app/schemas.py
from typing import Optional
from pydantic import BaseModel, Field


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


# ====================================================================
#  PERFIS
# ====================================================================
class PerfilBase(BaseModel):
    nome: str
    descricao: Optional[str] = None


class PerfilOut(PerfilBase):
    id: int
    ativo: bool

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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
