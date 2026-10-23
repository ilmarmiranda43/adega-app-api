# app/routers/adegas.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_db_session, require_platform_admin

import os
from datetime import datetime, timedelta, timezone
from sqlalchemy import select

router = APIRouter(
    prefix="/adegas",
    tags=["Adegas"],
)


@router.post(
    "/",
    response_model=schemas.AdegaOut,
    status_code=status.HTTP_201_CREATED,
)
def criar_adega(
    adega_in: schemas.AdegaCreate,
    db: Session = Depends(get_db_session),
    _usuario=Depends(require_platform_admin)
):
    """Cria uma nova adega (tenant)."""

    existente = (
        db.query(models.Adega)
        .filter(models.Adega.nome == adega_in.nome)
        .first()
    )
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe uma adega com esse nome.",
        )

    adega = models.Adega(
        nome=adega_in.nome,
        cnpj=adega_in.cnpj,
        telefone=adega_in.telefone,
        email=adega_in.email,
        whatsapp_numero=adega_in.whatsapp_numero,
        notificacao_ativa=adega_in.notificacao_ativa,
        plano="pago",
        status_assinatura="inativo",
    )

    db.add(adega)
    db.commit()
    db.refresh(adega)

    return adega


@router.get("/", response_model=List[schemas.AdegaOut])
def listar_adegas(
    db: Session = Depends(get_db_session),
    _usuario=Depends(require_platform_admin)
):
    """Lista todas as adegas."""
    adegas = db.query(models.Adega).order_by(models.Adega.nome).all()
    return adegas


@router.get("/{adega_id}", response_model=schemas.AdegaOut)
def obter_adega(
    adega_id: int,
    db: Session = Depends(get_db_session),
    _usuario=Depends(require_platform_admin)
):
    """Obtém detalhes de uma adega pelo ID."""
    adega = db.query(models.Adega).get(adega_id)
    if not adega:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Adega não encontrada.",
        )
    return adega


@router.put("/{adega_id}", response_model=schemas.AdegaOut)
def atualizar_adega(
    adega_id: int,
    adega_in: schemas.AdegaUpdate,
    db: Session = Depends(get_db_session),
    _usuario=Depends(require_platform_admin)
):
    """Atualiza dados básicos de uma adega."""
    adega = db.query(models.Adega).get(adega_id)
    if not adega:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Adega não encontrada.",
        )

    # aplica apenas campos informados
    if adega_in.nome is not None:
        adega.nome = adega_in.nome
    if adega_in.cnpj is not None:
        adega.cnpj = adega_in.cnpj
    if adega_in.telefone is not None:
        adega.telefone = adega_in.telefone
    if adega_in.email is not None:
        adega.email = adega_in.email
    if adega_in.whatsapp_numero is not None:
        adega.whatsapp_numero = adega_in.whatsapp_numero
    if adega_in.textmebot_api_key is not None:
        adega.textmebot_api_key = adega_in.textmebot_api_key
    if adega_in.notificacao_ativa is not None:
        adega.notificacao_ativa = adega_in.notificacao_ativa
    

    db.commit()
    db.refresh(adega)
    return adega


@router.delete(
    "/{adega_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def deletar_adega(
    adega_id: int,
    db: Session = Depends(get_db_session),
    _usuario=Depends(require_platform_admin)
):
    """Remove uma adega (cuidado em produção)."""
    adega = db.query(models.Adega).get(adega_id)
    if not adega:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Adega não encontrada.",
        )

    db.delete(adega)
    db.commit()
    return None

# ==========================================
# ADMINISTRAÇÃO DE TRIALS
# ==========================================

def buscar_adega_administravel(db: Session, adega_id: int):
    adega = db.execute(
        select(models.Adega)
        .where(models.Adega.id == adega_id)
        .with_for_update()
    ).scalar_one_or_none()

    if adega is None:
        raise HTTPException(
            status_code=404,
            detail="Adega não encontrada."
        )

    # Protege a adega interna da IMBEBI.
    possui_admin_global = db.query(models.Usuario.id).filter(
        models.Usuario.adega_id == adega_id,
        models.Usuario.is_platform_admin.is_(True)
    ).first()

    if possui_admin_global:
        raise HTTPException(
            status_code=403,
            detail="A conta administrativa não pode receber trial."
        )

    return adega

def garantir_utc(data):
    if data is None:
        return None

    if data.tzinfo is None:
        return data.replace(tzinfo=timezone.utc)

    return data.astimezone(timezone.utc)

def resposta_trial(adega):
    situacao = adega.status_assinatura

    # Vencimento calculado dinamicamente.
    if (
        situacao in ("trial", "expirado")
        and adega.trial_fim is not None
    ):
        if datetime.now(timezone.utc) >= garantir_utc(adega.trial_fim):
            situacao = "expirado"

    return {
        "adega_id": adega.id,
        "plano": adega.plano,
        "status_assinatura": situacao,
        "trial_inicio": adega.trial_inicio,
        "trial_fim": adega.trial_fim,
        "trial_dias": adega.trial_dias,
    }


@router.post(
    "/{adega_id}/trial",
    response_model=schemas.TrialStatusOut,
)
def conceder_trial(
    adega_id: int,
    configuracao: schemas.TrialConfig,
    db: Session = Depends(get_db_session),
    _usuario=Depends(require_platform_admin),
):
    try:
        adega = buscar_adega_administravel(db, adega_id)

        if adega.plano == "trial":
            raise HTTPException(
                status_code=409,
                detail="Esta adega já possui um trial. Use a rota de prorrogação.",
            )

        if adega.plano == "pago" and adega.status_assinatura == "ativo":
            raise HTTPException(
                status_code=409,
                detail="Esta adega possui assinatura paga ativa.",
            )

        agora = datetime.now(timezone.utc)

        adega.plano = "trial"
        adega.status_assinatura = "trial"
        adega.trial_inicio = agora
        adega.trial_dias = configuracao.dias
        adega.trial_fim = agora + timedelta(
            days=configuracao.dias
        )

        db.commit()
        db.refresh(adega)

        return resposta_trial(adega)

    except Exception:
        db.rollback()
        raise


@router.post(
    "/{adega_id}/trial/prorrogar",
    response_model=schemas.TrialStatusOut,
)
def prorrogar_trial(
    adega_id: int,
    prorrogacao: schemas.TrialProrrogacao,
    db: Session = Depends(get_db_session),
    _usuario=Depends(require_platform_admin),
):
    try:
        adega = buscar_adega_administravel(db, adega_id)

        if adega.plano != "trial" or not adega.trial_fim:
            raise HTTPException(
                status_code=400,
                detail="Esta adega não possui trial para prorrogar."
            )

        agora = datetime.now(timezone.utc)

        # Se expirado, reinicia a contagem a partir de agora.
        base = max(garantir_utc(adega.trial_fim), agora)

        adega.trial_fim = base + timedelta(
            days=prorrogacao.dias_adicionais
        )
        adega.trial_dias = (
            (adega.trial_fim - adega.trial_inicio).days
            if adega.trial_inicio else prorrogacao.dias_adicionais
        )
        adega.status_assinatura = "trial"

        db.commit()
        db.refresh(adega)

        return resposta_trial(adega)

    except Exception:
        db.rollback()
        raise


@router.get(
    "/{adega_id}/trial",
    response_model=schemas.TrialStatusOut,
)
def consultar_trial(
    adega_id: int,
    db: Session = Depends(get_db_session),
    _usuario=Depends(require_platform_admin),
):
    adega = db.query(models.Adega).filter(
        models.Adega.id == adega_id
    ).first()

    if adega is None:
        raise HTTPException(
            status_code=404,
            detail="Adega não encontrada."
        )

    return resposta_trial(adega)


@router.post(
    "/{adega_id}/ativar",
    response_model=schemas.TrialStatusOut,
)
def ativar_assinatura(
    adega_id: int,
    db: Session = Depends(get_db_session),
    _usuario=Depends(require_platform_admin),
):
    try:
        adega = buscar_adega_administravel(db, adega_id)

        adega.plano = "pago"
        adega.status_assinatura = "ativo"

        # Preserva as datas históricas do teste.
        db.commit()
        db.refresh(adega)

        return resposta_trial(adega)

    except Exception:
        db.rollback()
        raise
