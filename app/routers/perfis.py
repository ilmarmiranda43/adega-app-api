# app/routers/perfis.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..deps import get_db_session, require_roles
from .. import models, schemas

router = APIRouter(
    prefix="/perfis",
    tags=["Perfis"],
)


@router.get("/", response_model=list[schemas.PerfilOut])
def listar_perfis(
    incluir_inativos: bool = False,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_roles([1, 7])),  # só admin/master, e já retorna o usuário
):
    """
    Lista perfis da ADEGA do usuário logado.
    Por padrão, apenas ativos.
    Use ?incluir_inativos=true para trazer todos (da mesma adega).
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    query = db.query(models.Perfil).filter(
        models.Perfil.adega_id == usuario.adega_id
    )

    if not incluir_inativos:
        query = query.filter(models.Perfil.ativo == True)  # noqa: E712

    perfis = query.order_by(models.Perfil.nome).all()
    return perfis


@router.post(
    "/",
    response_model=schemas.PerfilOut,
    status_code=status.HTTP_201_CREATED,
)
def criar_perfil(
    perfil_in: schemas.PerfilBase,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_roles([1, 7])),
):
    """
    Cria perfil SEMPRE vinculado à adega do usuário logado.
    Ignora qualquer adega_id vindo do corpo.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    existente = (
        db.query(models.Perfil)
        .filter(
            models.Perfil.adega_id == usuario.adega_id,
            models.Perfil.nome.ilike(perfil_in.nome),
        )
        .first()
    )
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um perfil com esse nome nesta adega.",
        )

    perfil = models.Perfil(
        adega_id=usuario.adega_id,  # força a adega do usuário
        nome=perfil_in.nome,
        descricao=perfil_in.descricao,
        ativo=True,
    )
    db.add(perfil)
    db.commit()
    db.refresh(perfil)
    return perfil


@router.patch("/{perfil_id}/ativar", response_model=schemas.PerfilOut)
def ativar_perfil(
    perfil_id: int,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_roles([1, 7])),
):
    """
    Ativa um perfil apenas se ele pertencer à mesma adega do usuário.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    perfil = (
        db.query(models.Perfil)
        .filter(
            models.Perfil.id == perfil_id,
            models.Perfil.adega_id == usuario.adega_id,
        )
        .first()
    )
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil não encontrado.")
    perfil.ativo = True
    db.commit()
    db.refresh(perfil)
    return perfil


@router.patch("/{perfil_id}/inativar", response_model=schemas.PerfilOut)
def inativar_perfil(
    perfil_id: int,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_roles([1, 7])),
):
    """
    Inativa um perfil apenas se ele pertencer à mesma adega do usuário.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    perfil = (
        db.query(models.Perfil)
        .filter(
            models.Perfil.id == perfil_id,
            models.Perfil.adega_id == usuario.adega_id,
        )
        .first()
    )
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil não encontrado.")
    perfil.ativo = False
    db.commit()
    db.refresh(perfil)
    return perfil
