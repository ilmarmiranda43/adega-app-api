# app/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from .database import get_db
from . import models

from deps import SECRET_KEY, ALGORITHM

# Ajuste conforme seu endpoint de login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> models.Usuario:
    cred_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas ou expiradas.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int | None = payload.get("sub")
        if user_id is None:
            raise cred_exception
    except JWTError:
        raise cred_exception

    user = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
    if user is None:
        raise cred_exception
    return user


def get_current_admin_or_manager(
    current_user: models.Usuario = Depends(get_current_user),
) -> models.Usuario:
    # ajuste o nome do campo de perfil/role conforme seu model
    perfil = getattr(current_user, "perfil", None)

    if perfil not in ["Administrador", "Gerente"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso permitido apenas para Administrador ou Gerente.",
        )
    return current_user
