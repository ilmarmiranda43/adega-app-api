# app/deps.py
from typing import List

from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .database import get_db
from . import models, schemas

# Chave secreta simples pra começar (depois você pode jogar em variável de ambiente)
SECRET_KEY = "super-chave-ultra-secreta-da-adega"  # troque por algo mais forte
ALGORITHM = "HS256"

def get_db_session(db: Session = Depends(get_db)) -> Session:
    return db

def get_current_user(
    token: str,
    db: Session,
) -> models.Usuario:
    """Decodifica o token JWT e retorna o usuário do banco."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        perfil: str = payload.get("perfil")
        if user_id is None or perfil is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    usuario = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
    if usuario is None:
        raise credentials_exception
    return usuario

def get_current_user_from_header(
    db: Session = Depends(get_db_session),
    authorization: str = Depends(lambda: ""),
):
    """Lê o header Authorization: Bearer <token> e retorna o usuário."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação não informado",
        )
    token = authorization.removeprefix("Bearer ").strip()
    return get_current_user(token, db)


def require_roles(perfis_permitidos: List[str]):
    """Retorna uma dependência que exige que o usuário tenha um dos perfis."""

    def dependency(usuario: models.Usuario = Depends(get_current_user_from_header)):
        if usuario.perfil not in perfis_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para executar esta ação",
            )
        return usuario

    return dependency
