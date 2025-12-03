# app/routers/usuarios.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..deps import get_db_session, require_roles
from .. import models, schemas
from ..security import get_password_hash

router = APIRouter(
    prefix="/usuarios",
    tags=["Usuários"],
)


@router.get("/", response_model=list[schemas.UsuarioOut])
def listar_usuarios(
    adega_id: int | None = None,
    db: Session = Depends(get_db_session),
    _usuario=Depends(require_roles([1, 2])),  # admin ou gerente
):
    """
    Lista usuários.

    - Se `adega_id` for informado, lista apenas usuários daquela adega.
    - Se não for informado, lista todos (útil para admin geral).
    """
    query = db.query(models.Usuario)
    if adega_id is not None:
        query = query.filter(models.Usuario.adega_id == adega_id)

    usuarios = query.all()
    return usuarios


@router.get("/{usuario_id}", response_model=schemas.UsuarioOut)
def obter_usuario(
    usuario_id: int,
    db: Session = Depends(get_db_session),
    _usuario=Depends(require_roles([1, 2])),
):
    usuario = db.query(models.Usuario).get(usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return usuario


@router.post(
    "/",
    response_model=schemas.UsuarioOut,
    status_code=status.HTTP_201_CREATED,
)
def criar_usuario(
    usuario_in: schemas.UsuarioCreate,
    db: Session = Depends(get_db_session),
    _usuario=Depends(require_roles([1, 2])),
):
    """
    Cria um novo usuário já vinculado a um perfil existente (perfil_id)
    e a uma adega (adega_id).
    """
    existente = (
        db.query(models.Usuario)
        .filter(models.Usuario.email == usuario_in.email)
        .first()
    )
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="E-mail já está cadastrado.",
        )

    perfil = (
        db.query(models.Perfil)
        .filter(
            models.Perfil.id == usuario_in.perfil_id,
            models.Perfil.ativo == True,  # noqa: E712
        )
        .first()
    )
    if not perfil:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Perfil inválido ou inativo.",
        )

    adega = db.query(models.Adega).get(usuario_in.adega_id)
    if not adega:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Adega informada não existe.",
        )

    senha_hash = get_password_hash(usuario_in.senha)

    usuario = models.Usuario(
        nome=usuario_in.nome,
        email=usuario_in.email,
        senha_hash=senha_hash,
        perfil_id=usuario_in.perfil_id,
        adega_id=usuario_in.adega_id,
    )

    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    return usuario


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_usuario(
    usuario_id: int,
    db: Session = Depends(get_db_session),
    _usuario=Depends(require_roles([1, 2])),
):
    usuario = db.query(models.Usuario).get(usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    db.delete(usuario)
    db.commit()
    return None
