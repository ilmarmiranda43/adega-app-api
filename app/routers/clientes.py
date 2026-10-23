# app/routers/clientes.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_db_session, require_manage_clients

router = APIRouter(
    prefix="/clientes",
    tags=["Clientes"],
)


@router.post(
    "/",
    response_model=schemas.ClienteOut,
    status_code=status.HTTP_201_CREATED,
)
def criar_cliente(
    cliente: schemas.ClienteCreate,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_manage_clients),
):
    """
    Cria cliente SEMPRE vinculado à ADEGA do usuário logado.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    if cliente.email:
        existente = (
            db.query(models.Cliente)
            .filter(
                models.Cliente.email == cliente.email,
                models.Cliente.adega_id == usuario.adega_id,
            )
            .first()
        )
        if existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um cliente cadastrado com esse e-mail nesta adega.",
            )

    payload = cliente.dict()
    payload["adega_id"] = usuario.adega_id

    novo_cliente = models.Cliente(**payload)
    db.add(novo_cliente)
    db.commit()
    db.refresh(novo_cliente)
    return novo_cliente


@router.get("/", response_model=List[schemas.ClienteOut])
def listar_clientes(
    db: Session = Depends(get_db_session),
    usuario=Depends(require_manage_clients),
):
    """
    Lista clientes SOMENTE da ADEGA do usuário logado.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    clientes = (
        db.query(models.Cliente)
        .filter(models.Cliente.adega_id == usuario.adega_id)
        .order_by(models.Cliente.nome)
        .all()
    )
    return clientes


@router.get("/{cliente_id}", response_model=schemas.ClienteOut)
def obter_cliente(
    cliente_id: int,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_manage_clients),
):
    """
    Retorna um cliente apenas se ele pertencer à ADEGA do usuário logado.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    cliente = (
        db.query(models.Cliente)
        .filter(
            models.Cliente.id == cliente_id,
            models.Cliente.adega_id == usuario.adega_id,
        )
        .first()
    )

    if cliente is None:raise HTTPException(status_code=404,detail="Cliente não encontrado nesta adega.")
    return cliente


@router.put("/{cliente_id}", response_model=schemas.ClienteOut)
def atualizar_cliente(
    cliente_id: int,
    dados: schemas.ClienteUpdate,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_manage_clients),
):
    """
    Atualiza cliente apenas se pertencer à ADEGA do usuário logado.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    cliente_db = (
        db.query(models.Cliente)
        .filter(
            models.Cliente.id == cliente_id,
            models.Cliente.adega_id == usuario.adega_id,
        )
        .first()
    )
    if not cliente_db:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        if campo in ("id", "adega_id"):
            continue

        setattr(cliente_db, campo, valor)

    db.commit()
    db.refresh(cliente_db)
    return cliente_db


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_cliente(
    cliente_id: int,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_manage_clients),
):
    """
    Deleta cliente apenas se pertencer à ADEGA do usuário logado.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    cliente_db = (
        db.query(models.Cliente)
        .filter(
            models.Cliente.id == cliente_id,
            models.Cliente.adega_id == usuario.adega_id,
        )
        .first()
    )
    if not cliente_db:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    db.delete(cliente_db)
    db.commit()
    return None
