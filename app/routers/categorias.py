# app/routers/categorias.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_db_session, require_roles, get_current_user

router = APIRouter(
    prefix="/categorias",
    tags=["Categorias"],
)


@router.get("/", response_model=List[schemas.CategoriaOut])
def listar_categorias(
    db: Session = Depends(get_db_session),
    usuario=Depends(get_current_user),
):
    """
    Retorna todas as categorias da ADEGA do usuário logado.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    categorias = (
        db.query(models.Categoria)
        .filter(models.Categoria.adega_id == usuario.adega_id)
        .order_by(models.Categoria.id)
        .all()
    )
    return categorias


@router.get("/{categoria_id}", response_model=schemas.CategoriaOut)
def obter_categoria(
    categoria_id: int,
    db: Session = Depends(get_db_session),
    usuario=Depends(get_current_user),
):
    """
    Retorna uma categoria apenas se pertencer à ADEGA do usuário logado.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    categoria = (
        db.query(models.Categoria)
        .filter(
            models.Categoria.id == categoria_id,
            models.Categoria.adega_id == usuario.adega_id,
        )
        .first()
    )
    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada",
        )
    return categoria


@router.post(
    "/", response_model=schemas.CategoriaOut, status_code=status.HTTP_201_CREATED
)
def criar_categoria(
    dados: schemas.CategoriaCreate,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_roles([1, 2, 7])),  # admin ou gerente
):
    """
    Cria categoria SEMPRE vinculada à ADEGA do usuário logado.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    payload = dados.dict()
    payload["adega_id"] = usuario.adega_id

    categoria = models.Categoria(**payload)
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    return categoria


@router.put("/{categoria_id}", response_model=schemas.CategoriaOut)
def atualizar_categoria(
    categoria_id: int,
    dados: schemas.CategoriaUpdate,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_roles([1, 2, 7])),
):
    """
    Atualiza categoria apenas se ela pertencer à ADEGA do usuário logado.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    categoria = (
        db.query(models.Categoria)
        .filter(
            models.Categoria.id == categoria_id,
            models.Categoria.adega_id == usuario.adega_id,
        )
        .first()
    )
    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada",
        )

    for campo, valor in dados.dict(exclude_unset=True).items():
        if campo == "adega_id":
            continue
        setattr(categoria, campo, valor)

    db.commit()
    db.refresh(categoria)
    return categoria


@router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_categoria(
    categoria_id: int,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_roles([1, 2, 7])),
):
    """
    Deleta categoria apenas se pertencer à ADEGA do usuário logado.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    categoria = (
        db.query(models.Categoria)
        .filter(
            models.Categoria.id == categoria_id,
            models.Categoria.adega_id == usuario.adega_id,
        )
        .first()
    )
    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada",
        )
    db.delete(categoria)
    db.commit()
    return None
