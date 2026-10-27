"""Gestão multi-tenant. Registrar no main.py com app.include_router(gestao.router).

MASTER é exclusivamente o perfil global legado de ID 7, desde que ativo e
pertencente à adega do usuário. Não confundir eh_admin da adega com MASTER.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, EmailStr, Field
from ..deps import get_db_session, get_current_user
from .. import models, schemas
from ..security import get_password_hash

router = APIRouter(prefix="/gestao", tags=["Gestão"])


def validar_perfil(usuario, db: Session):
    perfil = db.query(models.Perfil).filter(
        models.Perfil.id == usuario.perfil_id,
        models.Perfil.adega_id == usuario.adega_id,
        models.Perfil.ativo.is_(True),
    ).first()
    if perfil is None:
        raise HTTPException(status_code=403, detail="Perfil do usuário inválido ou inativo.")
    return perfil


def papel(usuario, db: Session):
    perfil = validar_perfil(usuario, db)
    # Compatibilidade com o MASTER já previsto no backend existente.
    master = usuario.perfil_id == 7
    gerencia = master or bool(perfil.eh_admin or perfil.pode_gerenciar_usuarios)
    if not gerencia:
        raise HTTPException(status_code=403, detail="Sem permissão para gerenciar usuários.")
    return master


def selecionar_adega(usuario, db: Session, adega_id: int | None):
    master = papel(usuario, db)
    destino = usuario.adega_id if adega_id is None else adega_id
    if destino != usuario.adega_id and not master:
        raise HTTPException(status_code=403, detail="Você só pode gerenciar sua própria adega.")
    if not db.query(models.Adega).filter(models.Adega.id == destino).first():
        raise HTTPException(status_code=404, detail="Adega inexistente.")
    return destino


@router.get("/me")
def meus_acessos(db: Session = Depends(get_db_session), usuario=Depends(get_current_user)):
    master = papel(usuario, db)
    return {"usuario_id": usuario.id, "adega_id": usuario.adega_id, "master": master,
            "pode_gerenciar_usuarios": True}


@router.get("/adegas", response_model=list[schemas.AdegaOut])
def listar_adegas(db: Session = Depends(get_db_session), usuario=Depends(get_current_user)):
    master = papel(usuario, db)
    consulta = db.query(models.Adega)
    if not master:
        consulta = consulta.filter(models.Adega.id == usuario.adega_id)
    return consulta.order_by(models.Adega.nome).all()


@router.get("/perfis", response_model=list[schemas.PerfilOut])
def listar_perfis(adega_id: int | None = None, db: Session = Depends(get_db_session),
                  usuario=Depends(get_current_user)):
    destino = selecionar_adega(usuario, db, adega_id)
    return db.query(models.Perfil).filter(models.Perfil.adega_id == destino).order_by(models.Perfil.nome).all()


@router.get("/usuarios", response_model=list[schemas.UsuarioOut])
def listar_usuarios(adega_id: int | None = None, db: Session = Depends(get_db_session),
                    usuario=Depends(get_current_user)):
    destino = selecionar_adega(usuario, db, adega_id)
    return db.query(models.Usuario).filter(models.Usuario.adega_id == destino).order_by(models.Usuario.nome).all()


class UsuarioGestaoCreate(BaseModel):
    nome: str = Field(min_length=2)
    email: EmailStr
    senha: str = Field(min_length=6, max_length=72)
    perfil_id: int
    adega_id: int


@router.post("/usuarios", response_model=schemas.UsuarioOut, status_code=status.HTTP_201_CREATED)
def criar_usuario(dados: UsuarioGestaoCreate, db: Session = Depends(get_db_session),
                  usuario=Depends(get_current_user)):
    destino = selecionar_adega(usuario, db, dados.adega_id)
    perfil = db.query(models.Perfil).filter(
        models.Perfil.id == dados.perfil_id,
        models.Perfil.adega_id == destino,
        models.Perfil.ativo.is_(True),
    ).first()
    if perfil is None:
        raise HTTPException(status_code=400, detail="Perfil inválido, inativo ou de outra adega.")
    # Perfil 7 é reservado ao administrador global: nunca conceder via cadastro.
    if dados.perfil_id == 7:
        raise HTTPException(status_code=403, detail="O perfil global não pode ser atribuído por cadastro.")
    if db.query(models.Usuario).filter(models.Usuario.email == dados.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado.")
    novo = models.Usuario(nome=dados.nome.strip(), email=str(dados.email),
                          senha_hash=get_password_hash(dados.senha),
                          perfil_id=dados.perfil_id, adega_id=destino)
    db.add(novo)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Não foi possível salvar: conflito de dados.")
    db.refresh(novo)
    return novo
