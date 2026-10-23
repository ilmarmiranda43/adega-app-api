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
    db: Session = Depends(get_db_session),
    usuario=Depends(require_roles([1, 2, 7])),  # admin ou gerente
):
    """
    Lista usuários SOMENTE da adega do usuário logado.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    query = db.query(models.Usuario).filter(
        models.Usuario.adega_id == usuario.adega_id
    )

    usuarios = query.all()
    return usuarios


@router.get("/{usuario_id}", response_model=schemas.UsuarioOut)
def obter_usuario(
    usuario_id: int,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_roles([1, 2, 7])),
):
    """
    Busca um usuário apenas se ele pertencer à adega do usuário logado.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    alvo = (
        db.query(models.Usuario)
        .filter(
            models.Usuario.id == usuario_id,
            models.Usuario.adega_id == usuario.adega_id,
        )
        .first()
    )
    if not alvo:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return alvo


@router.post(
    "/",
    response_model=schemas.UsuarioOut,
    status_code=status.HTTP_201_CREATED,
)
def criar_usuario(
    usuario_in: schemas.UsuarioCreate,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_roles([1, 2, 7])),
):
    """
    Cria um novo usuário SEMPRE vinculado à mesma adega do usuário logado.
    Ignora adega_id vindo do body.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

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

    # Perfil precisa existir e estar ativo (opcional: você pode validar que é da mesma adega)
    perfil = (
        db.query(models.Perfil)
        .filter(
            models.Perfil.id == usuario_in.perfil_id,
            models.Perfil.adega_id == usuario.adega_id,
            models.Perfil.ativo.is_(True),
        )
        .first()
    )
    if not perfil:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Perfil inválido ou inativo.",
        )

    # Adega: sempre a mesma do usuário logado
    adega = db.query(models.Adega).get(usuario.adega_id)
    if not adega:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Adega vinculada ao usuário não existe.",
        )

    senha_hash = get_password_hash(usuario_in.senha)

    novo_usuario = models.Usuario(
        nome=usuario_in.nome,
        email=usuario_in.email,
        senha_hash=senha_hash,
        perfil_id=usuario_in.perfil_id,
        adega_id=usuario.adega_id,
    )

    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)

    return novo_usuario


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_usuario(
    usuario_id: int,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_roles([1, 2, 7])),
):
    """
    Exclui usuário apenas se ele pertencer à mesma adega do usuário logado.
    """
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    alvo = (
        db.query(models.Usuario)
        .filter(
            models.Usuario.id == usuario_id,
            models.Usuario.adega_id == usuario.adega_id,
        )
        .first()
    )
    if not alvo:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    db.delete(alvo)
    db.commit()
    return None
