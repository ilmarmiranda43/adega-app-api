# app/routers/produtos.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_db_session, require_roles, get_current_user

router = APIRouter(
    prefix="/produtos",
    tags=["Produtos"],
)


@router.get("/", response_model=List[schemas.ProdutoOut])
def listar_produtos(
    db: Session = Depends(get_db_session),
    usuario=Depends(get_current_user),
):
    """
    Retorna todos os produtos da ADEGA do usuário logado.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    produtos = (
        db.query(models.Produto)
        .filter(models.Produto.adega_id == usuario.adega_id)
        .order_by(models.Produto.id)
        .all()
    )
    return produtos


@router.get("/{produto_id}", response_model=schemas.ProdutoOut)
def obter_produto(
    produto_id: int,
    db: Session = Depends(get_db_session),
    usuario=Depends(get_current_user),
):
    """
    Retorna um produto apenas se pertencer à adega do usuário.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    produto = (
        db.query(models.Produto)
        .filter(
            models.Produto.id == produto_id,
            models.Produto.adega_id == usuario.adega_id,
        )
        .first()
    )
    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado",
        )
    return produto


@router.post(
    "/",
    response_model=schemas.ProdutoOut,
    status_code=status.HTTP_201_CREATED,
)
def criar_produto(
    dados: schemas.ProdutoCreate,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_roles([1, 2])),  # admin ou gerente da adega
):
    """
    Cria produto SEMPRE vinculado à adega do usuário logado.
    Ignora qualquer adega_id no body.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    data = dados.dict()
    # força a adega do usuário
    data["adega_id"] = usuario.adega_id

    produto = models.Produto(**data)
    db.add(produto)
    db.commit()
    db.refresh(produto)
    return produto


@router.put("/{produto_id}", response_model=schemas.ProdutoOut)
def atualizar_produto(
    produto_id: int,
    dados: schemas.ProdutoUpdate,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_roles([1, 2])),
):
    """
    Atualiza produto apenas se ele pertencer à adega do usuário.
    Não permite trocar a adega do produto.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    produto = (
        db.query(models.Produto)
        .filter(
            models.Produto.id == produto_id,
            models.Produto.adega_id == usuario.adega_id,
        )
        .first()
    )
    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado",
        )

    for campo, valor in dados.dict(exclude_unset=True).items():
        if campo == "adega_id":
            continue  # nunca deixar trocar a adega
        setattr(produto, campo, valor)

    db.commit()
    db.refresh(produto)
    return produto


@router.delete("/{produto_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_produto(
    produto_id: int,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_roles([1, 2])),
):
    """
    Deleta produto apenas se pertencer à adega do usuário.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    produto = (
        db.query(models.Produto)
        .filter(
            models.Produto.id == produto_id,
            models.Produto.adega_id == usuario.adega_id,
        )
        .first()
    )
    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado",
        )
    db.delete(produto)
    db.commit()
    return None
