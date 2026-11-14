# app/routers/produtos.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .. import models, schemas
from ..deps import (
    get_db_session,
    require_active_subscription,
    require_manage_products,
)

router = APIRouter(
    prefix="/produtos",
    tags=["Produtos"],
)


@router.get("/", response_model=List[schemas.ProdutoOut])
def listar_produtos(
    db: Session = Depends(get_db_session),
    usuario=Depends(require_active_subscription),
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


def salvar_com_codigo(db, produto):
    if produto.codigo_barras:
        existente = db.query(models.Produto).filter(
            models.Produto.adega_id == produto.adega_id,
            models.Produto.codigo_barras == produto.codigo_barras,
            models.Produto.id != produto.id if produto.id is not None else True,
        ).first()
        if existente:
            db.rollback()
            raise HTTPException(409, "Código de barras já cadastrado nesta adega.")
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if getattr(getattr(exc.orig, "diag", None), "constraint_name", None) == "produtos_adega_codigo_barras_key" or "produtos.adega_id, produtos.codigo_barras" in str(exc.orig):
            raise HTTPException(409, "Código de barras já cadastrado nesta adega.") from exc
        raise HTTPException(409, "Não foi possível salvar. Verifique categoria e dados vinculados.") from exc
    db.refresh(produto)


@router.get("/codigo-barras/{codigo}", response_model=schemas.ProdutoOut)
def buscar_codigo_barras(codigo: str, db: Session = Depends(get_db_session), usuario=Depends(require_active_subscription)):
    if getattr(usuario, "adega_id", None) is None:
        raise HTTPException(400, "Usuário não está vinculado a nenhuma adega.")
    produto = db.query(models.Produto).filter(
        models.Produto.adega_id == usuario.adega_id,
        models.Produto.codigo_barras == codigo.strip(),
    ).first()
    if produto is None:
        raise HTTPException(404, "Código de barras não cadastrado nesta adega.")
    return produto


@router.get("/{produto_id}", response_model=schemas.ProdutoOut)
def obter_produto(
    produto_id: int,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_active_subscription),
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
    usuario=Depends(require_manage_products),
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

    data = dados.model_dump()
    # força a adega do usuário
    data["adega_id"] = usuario.adega_id

    produto = models.Produto(**data)
    db.add(produto)
    salvar_com_codigo(db, produto)
    return produto


@router.put("/{produto_id}", response_model=schemas.ProdutoOut)
def atualizar_produto(
    produto_id: int,
    dados: schemas.ProdutoUpdate,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_manage_products),
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

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        if campo == "adega_id":
            continue  # nunca deixar trocar a adega
        setattr(produto, campo, valor)

    salvar_com_codigo(db, produto)
    return produto


@router.delete("/{produto_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_produto(
    produto_id: int,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_manage_products),
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
