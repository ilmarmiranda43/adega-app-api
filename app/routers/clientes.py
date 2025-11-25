# routers/clientes.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas
from ..database import get_db
from ..dependencies import get_current_admin_or_manager

router = APIRouter(
    prefix="/clientes",
    tags=["Clientes"],
)


@router.post("/", response_model=schemas.ClienteOut, status_code=status.HTTP_201_CREATED)
def criar_cliente(
    cliente: schemas.ClienteCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_admin_or_manager),
):
    if cliente.email:
        existente = db.query(models.Cliente).filter(models.Cliente.email == cliente.email).first()
        if existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um cliente cadastrado com esse e-mail."
            )

    novo_cliente = models.Cliente(**cliente.dict())
    db.add(novo_cliente)
    db.commit()
    db.refresh(novo_cliente)
    return novo_cliente


@router.get("/", response_model=List[schemas.ClienteOut])
def listar_clientes(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_admin_or_manager),
):
    print("Tentando listar clientes...")
    clientes = db.query(models.Cliente).order_by(models.Cliente.nome).all()
    return clientes


@router.get("/{cliente_id}", response_model=schemas.ClienteOut)
def obter_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_admin_or_manager),
):
    cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    return cliente


@router.put("/{cliente_id}", response_model=schemas.ClienteOut)
def atualizar_cliente(
    cliente_id: int,
    dados: schemas.ClienteUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_admin_or_manager),
):
    cliente_db = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if not cliente_db:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    for campo, valor in dados.dict(exclude_unset=True).items():
        setattr(cliente_db, campo, valor)

    db.commit()
    db.refresh(cliente_db)
    return cliente_db


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_admin_or_manager),
):
    cliente_db = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if not cliente_db:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    db.delete(cliente_db)
    db.commit()
    return
