# app/routers/auth.py
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_db_session, SECRET_KEY, ALGORITHM

router = APIRouter(
    prefix="/auth",
    tags=["Autenticação"],
)

# usa Argon2 em vez de bcrypt
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto",)


def hash_password(password: str) -> str:
    """
    Gera o hash da senha usando Argon2.
    (sem limite prático de 72 bytes como o bcrypt)
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, senha_hash: str) -> bool:
    """
    Verifica se a senha informada confere com o hash armazenado.
    """
    return pwd_context.verify(plain_password, senha_hash)


def create_access_token(user_id: int, perfil: str, expires_minutes: int = 60):
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode = {"sub": user_id, "perfil": perfil, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/registrar", response_model=schemas.UsuarioOut)
def registrar_usuario(
    dados: schemas.UsuarioCreate,
    db: Session = Depends(get_db_session),
):
    existente = (
        db.query(models.Usuario)
        .filter(models.Usuario.email == dados.email)
        .first()
    )
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="E-mail já cadastrado",
        )

    usuario = models.Usuario(
        nome=dados.nome,
        email=dados.email,
        senha_hash=hash_password(dados.senha),
        perfil=dados.perfil,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.post("/login", response_model=schemas.TokenOut)
def login(
    credenciais: schemas.LoginRequest,
    db: Session = Depends(get_db_session),
):
    usuario = (
        db.query(models.Usuario)
        .filter(models.Usuario.email == credenciais.email)
        .first()
    )
    if not usuario or not verify_password(
        credenciais.senha, usuario.senha_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos",
        )

    token = create_access_token(user_id=usuario.id, perfil=usuario.perfil)
    return schemas.TokenOut(
        access_token=token,
        user=schemas.UsuarioOut.from_orm(usuario),
    )
