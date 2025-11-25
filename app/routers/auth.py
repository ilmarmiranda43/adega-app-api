# app/routers/auth.py
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from sqlalchemy.orm import Session
from app.security import verify_password, get_password_hash

from .. import models, schemas
from ..deps import get_db_session, SECRET_KEY, ALGORITHM

ACCESS_TOKEN_EXPIRE_MINUTES = 600  # exemplo

router = APIRouter(
    prefix="/auth",
    tags=["Autenticação"],
)

def create_access_token(user_id: int, perfil_id: int, expires_delta: timedelta | None = None, ) -> str:
    to_encode = {"user_id": user_id, "perfil_id": perfil_id, }

    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = datetime.now(timezone.utc) + expires_delta
    to_encode["exp"] = expire

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
        senha_hash="123456",
        perfil=dados.perfil,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.post("/login", response_model=schemas.TokenOut)
def login(credenciais: schemas.LoginRequest,db: Session = Depends(get_db_session),):
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

    token = create_access_token(user_id=usuario.id, perfil_id=usuario.perfil_id)

    usuario_out = schemas.UsuarioOut.model_validate(usuario)

    return schemas.TokenOut(
        access_token=token,
        token_type="bearer",
        user=usuario_out,
    )
