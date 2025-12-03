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
    _usuario=Depends(require_roles([1, 2])),  # admin ou gerente
):
    # Verifica se o produto existe
    produto = (
        db.query(models.Produto)
        .filter(models.Produto.id == entrada.produto_id)
        .first()
    )
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")

    dados = entrada.dict()

    # Garante que SEMPRE haverá uma data de entrada
    if not dados.get("criado_em"):
        dados["criado_em"] = datetime.utcnow()

    nova_entrada = models.Estoque(**dados)
    db.add(nova_entrada)
    db.commit()
    db.refresh(nova_entrada)
    return nova_entrada


@router.get("/", response_model=List[schemas.EstoqueOut])
def listar_estoque(
    db: Session = Depends(get_db_session),
    _usuario=Depends(require_roles([1, 2])),
):
    itens = (
        db.query(models.Estoque)
        .order_by(models.Estoque.criado_em.desc())
        .all()
    )
    return itens


@router.get("/produto/{produto_id}", response_model=List[schemas.EstoqueOut])
def listar_estoque_por_produto(
    produto_id: int,
    db: Session = Depends(get_db_session),
    _usuario=Depends(require_roles([1, 2])),
):
    itens = (
        db.query(models.Estoque)
        .filter(models.Estoque.produto_id == produto_id)
        .all()
    )
    return itens


@router.get("/{estoque_id}", response_model=schemas.EstoqueOut)
def obter_entrada_estoque(
    estoque_id: int,
    db: Session = Depends(get_db_session),
    _usuario=Depends(require_roles([1, 2])),
):
    item = (
        db.query(models.Estoque)
        .filter(models.Estoque.id == estoque_id)
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
    _usuario=Depends(require_roles([1, 2])),
):
    item_db = (
        db.query(models.Estoque)
        .filter(models.Estoque.id == estoque_id)
        .first()
    )
    if not item_db:
        raise HTTPException(
            status_code=404, detail="Entrada de estoque não encontrada."
        )

    for campo, valor in dados.dict(exclude_unset=True).items():
        setattr(item_db, campo, valor)

    db.commit()
    db.refresh(item_db)
    return item_db


@router.delete("/{estoque_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_entrada_estoque(
    estoque_id: int,
    db: Session = Depends(get_db_session),
    _usuario=Depends(require_roles([1, 2])),
):
    item_db = (
        db.query(models.Estoque)
        .filter(models.Estoque.id == estoque_id)
        .first()
    )
    if not item_db:
        raise HTTPException(
            status_code=404, detail="Entrada de estoque não encontrada."
        )

    db.delete(item_db)
    db.commit()
    return None
