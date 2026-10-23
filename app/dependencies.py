# app/dependencies.py
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from .database import get_db
from . import models

import os

# SECRET_KEY = "app-adega-miranda"  # troque por algo mais forte
SECRET_KEY = os.environ["SECRET_KEY"]
ALGORITHM = "HS256"

# Ajuste conforme seu endpoint de login
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    # credentials.scheme -> "Bearer"
    # credentials.credentials -> o token em si

    token = credentials.credentials  # <-- ESSA é a string do JWT

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int | None = payload.get("user_id")  # ou "sub", depende de como você gerou o token
        if user_id is None:
            raise credentials_exception

    except JWTError as e:
        print("Erro ao decodificar JWT:", e)
        raise credentials_exception

    user = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
    if user is None:
        raise credentials_exception

    return user


def get_current_admin_or_manager(
    current_user: models.Usuario = Depends(get_current_user),
) -> models.Usuario:
    
    # ajuste o nome do campo de perfil/role conforme seu model
    # perfil = getattr(current_user, "perfil", None)

    # if perfil not in ["Administrador", "Gerente"]:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Acesso permitido apenas para Administrador ou Gerente.",
    #     )
    # return current_user
    
    if current_user.perfil_id not in (1, 2):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar este recurso.",
        )

    print("Acesso liberado para Admin/Gerente")
    return current_user
