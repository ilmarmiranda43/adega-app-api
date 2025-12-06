# app/routers/estoque.py
from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_db_session, require_roles

router = APIRouter(
    prefix="/estoque",
    tags=["Estoque"],
)


@router.post(
    "/",
    response_model=schemas.EstoqueOut,
    status_code=status.HTTP_201_CREATED,
)
def criar_entrada_estoque(
    entrada: schemas.EstoqueCreate,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_roles([1, 2])),  # admin ou gerente
):
    """
    Cria entrada de estoque para PRODUTO e ADEGA do usuário logado.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    # Verifica se o produto existe e pertence à mesma adega
    produto = (
        db.query(models.Produto)
        .filter(
            models.Produto.id == entrada.produto_id,
            models.Produto.adega_id == usuario.adega_id,
        )
        .first()
    )
    if not produto:
        raise HTTPException(
            status_code=404,
            detail="Produto não encontrado para esta adega.",
        )

    dados = entrada.dict()

    # Garante que SEMPRE haverá uma data de entrada
    if not dados.get("criado_em"):
        dados["criado_em"] = datetime.utcnow()

    # força a adega da entrada de estoque
    dados["adega_id"] = usuario.adega_id

    nova_entrada = models.Estoque(**dados)
    db.add(nova_entrada)
    db.commit()
    db.refresh(nova_entrada)
    return nova_entrada


@router.get("/", response_model=List[schemas.EstoqueOut])
def listar_estoque(
    db: Session = Depends(get_db_session),
    usuario=Depends(require_roles([1, 2])),
):
    """
    Lista entradas de estoque SOMENTE da ADEGA do usuário logado.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    itens = (
        db.query(models.Estoque)
        .filter(models.Estoque.adega_id == usuario.adega_id)
        .order_by(models.Estoque.criado_em.desc())
        .all()
    )
    return itens


@router.get("/produto/{produto_id}", response_model=List[schemas.EstoqueOut])
def listar_estoque_por_produto(
    produto_id: int,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_roles([1, 2])),
):
    """
    Lista entradas de estoque de um produto, SOMENTE da ADEGA do usuário logado.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    itens = (
        db.query(models.Estoque)
        .filter(
            models.Estoque.produto_id == produto_id,
            models.Estoque.adega_id == usuario.adega_id,
        )
        .order_by(models.Estoque.criado_em.desc())
        .all()
    )
    return itens


@router.get("/{estoque_id}", response_model=schemas.EstoqueOut)
def obter_entrada_estoque(
    estoque_id: int,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_roles([1, 2])),
):
    """
    Retorna uma entrada de estoque apenas se pertencer à ADEGA do usuário logado.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    item = (
        db.query(models.Estoque)
        .filter(
            models.Estoque.id == estoque_id,
            models.Estoque.adega_id == usuario.adega_id,
        )
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=404, detail="Entrada de estoque não encontrada."
        )
    return item


@router.put("/{estoque_id}", response_model=schemas.EstoqueOut)
def atualizar_entrada_estoque(
    estoque_id: int,
    dados: schemas.EstoqueUpdate,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_roles([1, 2])),
):
    """
    Atualiza entrada de estoque apenas se pertencer à ADEGA do usuário logado.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    item_db = (
        db.query(models.Estoque)
        .filter(
            models.Estoque.id == estoque_id,
            models.Estoque.adega_id == usuario.adega_id,
        )
        .first()
    )
    if not item_db:
        raise HTTPException(
            status_code=404, detail="Entrada de estoque não encontrada."
        )

    for campo, valor in dados.dict(exclude_unset=True).items():
        if campo == "adega_id":
            continue
        setattr(item_db, campo, valor)

    db.commit()
    db.refresh(item_db)
    return item_db


@router.delete("/{estoque_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_entrada_estoque(
    estoque_id: int,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_roles([1, 2])),
):
    """
    Deleta entrada de estoque apenas se pertencer à ADEGA do usuário logado.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    item_db = (
        db.query(models.Estoque)
        .filter(
            models.Estoque.id == estoque_id,
            models.Estoque.adega_id == usuario.adega_id,
        )
        .first()
    )
    if not item_db:
        raise HTTPException(
            status_code=404, detail="Entrada de estoque não encontrada."
        )

    db.delete(item_db)
    db.commit()
    return None
