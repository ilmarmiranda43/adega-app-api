from typing import List
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .database import get_db
from . import models
from datetime import datetime, timezone

import os


# SECRET_KEY = "app-adega-miranda"
SECRET_KEY = os.environ["SECRET_KEY"]
ALGORITHM = "HS256"

security = HTTPBearer()  # isso cria o esquema HTTPBearer no Swagger


def get_db_session(db: Session = Depends(get_db)) -> Session:
    return db


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db_session),
) -> models.Usuario:
    token = credentials.credentials  # o Swagger já manda "Bearer ..." no header

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError as e:
        raise credentials_exception

    usuario = db.query(models.Usuario).filter(models.Usuario.id == int(user_id)).first()
    if usuario is None:
        raise credentials_exception

    return usuario


def require_roles(perfis_permitidos: List[int]):
    def dependency(usuario: models.Usuario = Depends(get_current_user)):
        perfil_usuario = getattr(usuario, "perfil_id", None)
        if perfil_usuario not in perfis_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para executar esta ação",
            )
        return usuario

    return dependency


def require_platform_admin(
    usuario: models.Usuario = Depends(get_current_user),
) -> models.Usuario:
    """
    Permite acesso somente a administradores globais
    da plataforma IMBEBI Tec.
    """

    if usuario.is_platform_admin is not True:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso exclusivo do administrador da plataforma.",
        )

    return usuario


def require_active_subscription(
    usuario: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> models.Usuario:
    """
    Autoriza operações somente para adegas
    com assinatura ativa ou trial válido.
    """

    if usuario.adega_id is None:
        raise HTTPException(
            status_code=403,
            detail="Usuário sem adega vinculada.",
        )

    adega = (
        db.query(models.Adega)
        .filter(models.Adega.id == usuario.adega_id)
        .first()
    )

    if adega is None:
        raise HTTPException(
            status_code=403,
            detail="Adega não encontrada.",
        )

    # Mantém o acesso das adegas com assinatura paga ativa.
    if adega.plano == "pago" and adega.status_assinatura == "ativo":
        return usuario

    # A tela Administração grava o trial na tabela adega_trials.
    # Consultar SEMPRE pelo adega_id do usuário autenticado.
    try:
        registro = db.execute(
            text("""
                SELECT ativo, dias, iniciado_em
                FROM adega_trials
                WHERE adega_id = :adega_id
            """),
            {"adega_id": usuario.adega_id},
        ).mappings().first()
    except SQLAlchemyError:
        # Não libera acesso por engano quando a tabela não está acessível.
        # Verificar migração 20261031_adega_trials.sql e logs do backend.
        raise HTTPException(
            status_code=503,
            detail="Não foi possível verificar o período de teste. Contate o suporte.",
        )

    if registro is not None:
        if not registro["ativo"]:
            raise HTTPException(
                status_code=403,
                detail="Período de teste desabilitado para esta adega.",
            )

        inicio = registro["iniciado_em"]
        if inicio is None:
            raise HTTPException(
                status_code=403,
                detail="Período de teste não iniciado.",
            )

        if inicio.tzinfo is None:
            inicio = inicio.replace(tzinfo=timezone.utc)
        else:
            inicio = inicio.astimezone(timezone.utc)

        from datetime import timedelta
        vencimento = inicio + timedelta(days=int(registro["dias"]))
        if datetime.now(timezone.utc) < vencimento:
            return usuario

        raise HTTPException(
            status_code=403,
            detail="Seu período de teste expirou.",
        )

    # Sem configuração na tabela nova, mantém a compatibilidade com o
    # trial legado gravado diretamente na tabela adegas.
    if (
        adega.plano == "trial"
        and adega.status_assinatura == "trial"
        and adega.trial_fim is not None
    ):
        vencimento = adega.trial_fim
        if vencimento.tzinfo is None:
            vencimento = vencimento.replace(tzinfo=timezone.utc)
        else:
            vencimento = vencimento.astimezone(timezone.utc)
        if datetime.now(timezone.utc) < vencimento:
            return usuario
        raise HTTPException(status_code=403, detail="Seu período de teste expirou.")

    raise HTTPException(
        status_code=403,
        detail="Assinatura inativa. Entre em contato com a IMBEBI Tec.",
    )


def require_manage_products(
    usuario: models.Usuario = Depends(require_active_subscription),
    db: Session = Depends(get_db_session),
) -> models.Usuario:
    """
    Exige assinatura ativa e permissão
    para gerenciar produtos.
    """

    perfil = (
        db.query(models.Perfil)
        .filter(
            models.Perfil.id == usuario.perfil_id,
            models.Perfil.adega_id == usuario.adega_id,
            models.Perfil.ativo.is_(True),
        )
        .first()
    )

    if perfil is None:
        raise HTTPException(
            status_code=403,
            detail="Perfil inválido ou inativo.",
        )

    if not (
        perfil.eh_admin
        or perfil.pode_gerenciar_estoque
    ):
        raise HTTPException(
            status_code=403,
            detail="Sem permissão para gerenciar produtos.",
        )

    return usuario

def require_manage_clients(
    usuario: models.Usuario = Depends(require_active_subscription),
    db: Session = Depends(get_db_session),
) -> models.Usuario:
    """
    Exige assinatura válida e permissão
    para gerenciar clientes da própria adega.
    """

    perfil = (
        db.query(models.Perfil)
        .filter(
            models.Perfil.id == usuario.perfil_id,
            models.Perfil.adega_id == usuario.adega_id,
            models.Perfil.ativo.is_(True),
        )
        .first()
    )

    if perfil is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Perfil inválido ou inativo.",
        )

    if not (
        perfil.eh_admin
        or perfil.pode_gerenciar_clientes
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para gerenciar clientes.",
        )

    return usuario

def require_manage_users(
    usuario: models.Usuario = Depends(require_active_subscription),
    db: Session = Depends(get_db_session),
) -> models.Usuario:
    """
    Exige assinatura válida e permissão
    para gerenciar usuários da própria adega.
    """

    perfil = (
        db.query(models.Perfil)
        .filter(
            models.Perfil.id == usuario.perfil_id,
            models.Perfil.adega_id == usuario.adega_id,
            models.Perfil.ativo.is_(True),
        )
        .first()
    )

    if perfil is None:
        raise HTTPException(
            status_code=403,
            detail="Perfil inválido ou inativo.",
        )

    if not (
        perfil.eh_admin
        or perfil.pode_gerenciar_usuarios
    ):
        raise HTTPException(
            status_code=403,
            detail="Sem permissão para gerenciar usuários.",
        )

    return usuario
