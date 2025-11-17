# app/schemas.py
from typing import Optional
from pydantic import BaseModel, Field


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
        from_attributes = True  # substitui orm_mode=True no Pydantic v2

# ----------------------------------------------------------------------------------------------------
#  Categorias
# ----------------------------------------------------------------------------------------------------

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
        orm_mode = True