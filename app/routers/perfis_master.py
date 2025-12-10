# app/routers/perfis_master.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app import models  # Perfil, Adega
from app.dependencies import get_current_user  # ajuste para o seu projeto
from ..schemas import PerfilOut, PerfilCreate, PerfilUpdate

router = APIRouter(
    prefix="/perfis",
    tags=["perfis"],
)


def ensure_master(current_user):
    if getattr(current_user, "papel", None) != "master":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas usuário master pode gerenciar perfis.",
        )


@router.get("/", response_model=List[PerfilOut])
def listar_perfis(
    adega_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Lista perfis. Se adega_id não for informado, traz todos.
    Apenas usuário master pode acessar.
    """
    ensure_master(current_user)

    query = db.query(models.Perfil)
    if adega_id is not None:
        query = query.filter(models.Perfil.adega_id == adega_id)

    return query.order_by(models.Perfil.adega_id, models.Perfil.nome).all()


@router.post("/", response_model=PerfilOut, status_code=status.HTTP_201_CREATED)
def criar_perfil(
    perfil_in: PerfilCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ensure_master(current_user)

    perfil = models.Perfil(
        adega_id=perfil_in.adega_id,
        nome=perfil_in.nome,
        descricao=perfil_in.descricao,
        eh_admin=perfil_in.eh_admin,
        pode_gerenciar_usuarios=perfil_in.pode_gerenciar_usuarios,
        pode_gerenciar_estoque=perfil_in.pode_gerenciar_estoque,
        pode_gerenciar_clientes=perfil_in.pode_gerenciar_clientes,
        ativo=perfil_in.ativo if perfil_in.ativo is not None else True,
        criado_em=datetime.utcnow(),
        atualizado_em=datetime.utcnow(),
    )
    db.add(perfil)
    db.commit()
    db.refresh(perfil)
    return perfil


@router.put("/{perfil_id}", response_model=PerfilOut)
def atualizar_perfil(
    perfil_id: int,
    perfil_in: PerfilUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ensure_master(current_user)

    perfil = db.query(models.Perfil).filter(models.Perfil.id == perfil_id).first()
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil não encontrado.")

    for campo, valor in perfil_in.dict(exclude_unset=True).items():
        setattr(perfil, campo, valor)

    perfil.atualizado_em = datetime.utcnow()
    db.commit()
    db.refresh(perfil)
    return perfil


@router.delete("/{perfil_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_perfil(
    perfil_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ensure_master(current_user)

    perfil = db.query(models.Perfil).filter(models.Perfil.id == perfil_id).first()
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil não encontrado.")

    db.delete(perfil)
    db.commit()
    return
