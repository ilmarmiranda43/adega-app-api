from typing import List
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from .database import get_db
from . import models

SECRET_KEY = "app-adega-miranda"
ALGORITHM = "HS256"

security = HTTPBearer()  # isso cria o esquema HTTPBearer no Swagger


def get_db_session(db: Session = Depends(get_db)) -> Session:
    return db


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db_session),
) -> models.Usuario:
    token = credentials.credentials  # o Swagger já manda "Bearer ..." no header
    print("DEBUG Authorization header recebido:", credentials.scheme, token[:40] + "...")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print("DEBUG payload decodificado:", payload)
        user_id = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError as e:
        print("DEBUG erro ao decodificar JWT:", repr(e))
        raise credentials_exception

    usuario = db.query(models.Usuario).filter(models.Usuario.id == int(user_id)).first()
    if usuario is None:
        raise credentials_exception

    return usuario


def require_roles(perfis_permitidos: List[int]):
    def dependency(usuario: models.Usuario = Depends(get_current_user)):
        perfil_usuario = getattr(usuario, "perfil_id", None)
        print("DEBUG perfil do usuário (id):", perfil_usuario)

        if perfil_usuario not in perfis_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para executar esta ação",
            )
        return usuario

    return dependency
