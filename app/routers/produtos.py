# app/routers/produtos.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_db_session, require_roles

router = APIRouter(
    prefix="/produtos",
    tags=["Produtos"],
)


@router.get("/", response_model=List[schemas.ProdutoOut])
def listar_produtos(db: Session = Depends(get_db_session)):
    """Retorna todos os produtos ativos."""
    # produtos = db.query(models.Produto).filter(models.Produto.id).all()
    produtos = db.query(models.Produto).order_by(models.Produto.id).all()
    return produtos


@router.get("/{produto_id}", response_model=schemas.ProdutoOut)
def obter_produto(produto_id: int, db: Session = Depends(get_db_session)):
    produto = db.query(models.Produto).filter(models.Produto.id == produto_id).first()
    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado",
        )
    return produto


@router.post(
    "/", response_model=schemas.ProdutoOut, status_code=status.HTTP_201_CREATED
)
def criar_produto(
    dados: schemas.ProdutoCreate,
    db: Session = Depends(get_db_session),
    _usuario=Depends(require_roles([1, 2])),
):
    produto = models.Produto(**dados.dict())
    db.add(produto)
    db.commit()
    db.refresh(produto)
    return produto


@router.put("/{produto_id}", response_model=schemas.ProdutoOut)
def atualizar_produto(
    produto_id: int,
    dados: schemas.ProdutoUpdate,
    db: Session = Depends(get_db_session),
    _usuario=Depends(require_roles([1, 2])),
):
    produto = db.query(models.Produto).filter(models.Produto.id == produto_id).first()
    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado",
        )

    for campo, valor in dados.dict(exclude_unset=True).items():
        setattr(produto, campo, valor)

    db.commit()
    db.refresh(produto)
    return produto


@router.delete("/{produto_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_produto(produto_id: int, db: Session = Depends(get_db_session), _usuario=Depends(require_roles([1, 2]))):
    produto = db.query(models.Produto).filter(models.Produto.id == produto_id).first()
    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado",
        )
    db.delete(produto)
    db.commit()
    return None
