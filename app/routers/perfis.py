# app/routers/perfis.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter(
    prefix="/perfis",
    tags=["Perfis"],
)


@router.get("/", response_model=list[schemas.PerfilOut])
def listar_perfis(incluir_inativos: bool = False, db: Session = Depends(get_db)):
    """
    Lista perfis. Por padrão, apenas ativos.
    Use ?incluir_inativos=true para trazer todos.
    """
    query = db.query(models.Perfil)
    if not incluir_inativos:
        query = query.filter(models.Perfil.ativo == True)  # noqa: E712
    perfis = query.order_by(models.Perfil.nome).all()
    return perfis


@router.post("/", response_model=schemas.PerfilOut, status_code=status.HTTP_201_CREATED)
def criar_perfil(perfil_in: schemas.PerfilBase, db: Session = Depends(get_db)):
    """
    Cria um novo perfil.
    """
    existente = (
        db.query(models.Perfil)
        .filter(models.Perfil.nome.ilike(perfil_in.nome))
        .first()
    )
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um perfil com esse nome.",
        )

    perfil = models.Perfil(
        nome=perfil_in.nome,
        descricao=perfil_in.descricao,
        ativo=True,
    )
    db.add(perfil)
    db.commit()
    db.refresh(perfil)
    return perfil


@router.patch("/{perfil_id}/ativar", response_model=schemas.PerfilOut)
def ativar_perfil(perfil_id: int, db: Session = Depends(get_db)):
    perfil = db.query(models.Perfil).get(perfil_id)
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil não encontrado.")
    perfil.ativo = True
    db.commit()
    db.refresh(perfil)
    return perfil


@router.patch("/{perfil_id}/inativar", response_model=schemas.PerfilOut)
def inativar_perfil(perfil_id: int, db: Session = Depends(get_db)):
    perfil = db.query(models.Perfil).get(perfil_id)
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil não encontrado.")
    perfil.ativo = False
    db.commit()
    db.refresh(perfil)
    return perfil
