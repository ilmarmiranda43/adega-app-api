# app/routers/adegas.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_db_session, require_roles

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
    _usuario=Depends(require_roles([7])),  # apenas admin
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
    )

    db.add(adega)
    db.commit()
    db.refresh(adega)

    return adega


@router.get("/", response_model=List[schemas.AdegaOut])
def listar_adegas(
    db: Session = Depends(get_db_session),
    _usuario=Depends(require_roles([7])),  # apenas admin
):
    """Lista todas as adegas."""
    adegas = db.query(models.Adega).order_by(models.Adega.nome).all()
    return adegas


@router.get("/{adega_id}", response_model=schemas.AdegaOut)
def obter_adega(
    adega_id: int,
    db: Session = Depends(get_db_session),
    _usuario=Depends(require_roles([7])),
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
    _usuario=Depends(require_roles([7])),
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
    _usuario=Depends(require_roles([7])),
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
