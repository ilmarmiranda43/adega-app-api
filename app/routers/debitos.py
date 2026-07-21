# app/routers/debitos.py
import os
import re
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from ..schemas import DebitoCreate, DebitoOut, EnviarWhatsAppIn
from ..deps import get_current_user

router = APIRouter(prefix="/debitos", tags=["Débitos"])


def so_digitos(phone: str) -> str:
    return re.sub(r"\D+", "", phone or "")


def get_user_attr(user, key: str, default=None):
    """Suporta user como objeto (atributos) ou dict (chaves)."""
    if user is None:
        return default
    if isinstance(user, dict):
        return user.get(key, default)
    return getattr(user, key, default)


def is_master(user) -> bool:
    """
    Ajuste se no seu projeto Master for outro perfil_id.
    Pelo que você mostrou antes, Master costuma ser perfil_id=7.
    """
    perfil_id = get_user_attr(user, "perfil_id", None)
    try:
        return int(perfil_id) == 7
    except Exception:
        return False


def enforce_debito_scope(db: Session, debito_id: int, user) -> dict:
    """
    Busca o débito e valida escopo multi-tenant:
    - Se o usuário tiver adega_id, só pode operar débitos daquela adega.
    - Se for Master (perfil_id=7), libera.
    """
    row = db.execute(
        text(
            """
            SELECT id, adega_id, cliente_id, valor, descricao, status, vencimento, criado_em,
                   COALESCE(whatsapp_enviado, false) as whatsapp_enviado
            FROM debitos_clientes
            WHERE id = :did
            """
        ),
        {"did": debito_id},
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Débito não encontrado.")

    user_adega_id = get_user_attr(user, "adega_id", None)

    # Se não é master e tem adega_id, restringe
    if (not is_master(user)) and user_adega_id is not None:
        try:
            if int(row["adega_id"]) != int(user_adega_id):
                raise HTTPException(status_code=403, detail="Acesso negado para este débito.")
        except ValueError:
            raise HTTPException(status_code=403, detail="Acesso negado para este débito.")

    return row


@router.post("/", response_model=DebitoOut)
def criar_debito(
    payload: DebitoCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    # Valida cliente pertence à adega (multi-tenant)
    cliente_sql = """
        SELECT id, telefone, eh_whatsapp
        FROM clientes
        WHERE id = :cid AND adega_id = :aid
    """
    cliente = db.execute(
        text(cliente_sql),
        {"cid": payload.cliente_id, "aid": payload.adega_id},
    ).mappings().first()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado para esta adega.")

    insert_sql = """
        INSERT INTO debitos_clientes (adega_id, cliente_id, valor, descricao, vencimento)
        VALUES (:aid, :cid, :valor, :descricao, :vencimento)
        RETURNING id, adega_id, cliente_id, valor, descricao, status, vencimento, criado_em, whatsapp_enviado
    """
    debito = db.execute(
        text(insert_sql),
        {
            "aid": payload.adega_id,
            "cid": payload.cliente_id,
            "valor": payload.valor,
            "descricao": payload.descricao,
            "vencimento": payload.vencimento,
        },
    ).mappings().first()

    db.commit()
    return debito


@router.get("/", response_model=list[DebitoOut])
def listar_debitos(
    adega_id: int = Query(...),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    q = """
    SELECT id, adega_id, cliente_id, valor, descricao, status, vencimento, criado_em, whatsapp_enviado
    FROM debitos_clientes
    WHERE adega_id = :aid
    """
    params = {"aid": adega_id}

    if status:
        q += " AND status = :status"
        params["status"] = status

    q += " ORDER BY criado_em DESC"

    rows = db.execute(text(q), params).mappings().all()
    return rows


# ✅ NOVO: fechar débito (marca como pago)
@router.post("/{debito_id}/fechar")
def fechar_debito(
    debito_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    row = enforce_debito_scope(db, debito_id, user)

    if row["status"] != "aberto":
        raise HTTPException(status_code=400, detail="Só é possível fechar débitos em aberto.")

    upd = db.execute(
        text(
            """
            UPDATE debitos_clientes
            SET status = 'pago'
            WHERE id = :did
            RETURNING id, adega_id, cliente_id, valor, descricao, status, vencimento, criado_em
            """
        ),
        {"did": debito_id},
    ).mappings().first()

    db.commit()
    return {"ok": True, "debito": upd}


# ✅ NOVO: marcar que WhatsApp foi enviado
@router.post("/{debito_id}/marcar-whatsapp")
def marcar_whatsapp(
    debito_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = enforce_debito_scope(db, debito_id, user)

    try:
        upd = db.execute(
            text(
                """
                UPDATE debitos_clientes
                SET whatsapp_enviado = true
                WHERE id = :did
                RETURNING id, adega_id, cliente_id, valor, descricao, status, vencimento, criado_em,
                          COALESCE(whatsapp_enviado, false) as whatsapp_enviado
                """
            ),
            {"did": debito_id},
        ).mappings().first()

        db.commit()
        return {"ok": True, "debito": upd}

    except Exception as e:
        # Se a coluna whatsapp_enviado não existir, aqui você vai cair.
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Não foi possível marcar WhatsApp como enviado. Verifique se existe a coluna whatsapp_enviado. Erro: {e}",
        )


@router.post("/{debito_id}/enviar-whatsapp")
async def enviar_whatsapp_debito(
    debito_id: int,
    body: EnviarWhatsAppIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    # valida escopo + existência
    _ = enforce_debito_scope(db, debito_id, user)

    row_sql = """
        SELECT d.id, d.adega_id, d.cliente_id, d.valor, d.descricao, d.vencimento, d.status,
               c.nome as cliente_nome, c.telefone, c.eh_whatsapp,
               a.nome as adega_nome
        FROM debitos_clientes d
        JOIN clientes c ON c.id = d.cliente_id
        JOIN adegas a ON a.id = d.adega_id
        WHERE d.id = :did
    """
    row = db.execute(text(row_sql), {"did": debito_id}).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Débito não encontrado.")

    if row["status"] != "aberto":
        raise HTTPException(status_code=400, detail="Só é possível enviar WhatsApp para débito em aberto.")

    if not row["telefone"]:
        raise HTTPException(status_code=400, detail="Cliente sem telefone cadastrado.")

    if row.get("eh_whatsapp") is False:
        raise HTTPException(status_code=400, detail="Cliente marcado como não-WhatsApp.")

    recipient = so_digitos(row["telefone"])
    if not recipient.startswith("55"):
        recipient = "55" + recipient

    # Monta mensagem padrão (ou usa a do front)
    if body.mensagem and body.mensagem.strip():
        message = body.mensagem.strip()
    else:
        valor = f"{row['valor']:.2f}".replace(".", ",")
        venc = row["vencimento"].strftime("%d/%m/%Y") if row["vencimento"] else "—"
        desc = row["descricao"] or "Débito avulso"
        message = (
            f"Olá, {row['cliente_nome']}! 😊\n"
            f"Consta um débito em aberto na {row['adega_nome']}\n"
            f"• Valor: R$ {valor}\n"
            f"• Vencimento: {venc}\n"
            f"• Descrição: {desc}\n\n"
            f"Se precisar, me chame por aqui."
        )

    baileys_url = os.getenv("BAILEYS_SERVICE_URL", "http://localhost:3001").rstrip("/")
    baileys_api_key = os.getenv("BAILEYS_API_KEY")

    if not baileys_api_key:
        raise HTTPException(status_code=500, detail="BAILEYS_API_KEY não configurada no servidor.")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{baileys_url}/send",
                headers={"X-API-Key": baileys_api_key},
                json={
                    "adega_id": row["adega_id"],
                    "telefone": recipient,
                    "mensagem": message,
                },
            )
    except httpx.RequestError as erro:
        raise HTTPException(
            status_code=503,
            detail=f"Não foi possível conectar ao serviço Baileys: {erro}",
        ) from erro

    try:
        resultado_baileys = resp.json()
    except ValueError:
        resultado_baileys = {"ok": False, "erro": resp.text}

    if resp.status_code != 200 or not resultado_baileys.get("ok"):
        detalhe = resultado_baileys.get("erro", "O serviço Baileys recusou o envio.")
        raise HTTPException(status_code=502, detail=detalhe)

    # ✅ bônus: marca como enviado automaticamente (se coluna existir)
    try:
        db.execute(
            text("UPDATE debitos_clientes SET whatsapp_enviado = true WHERE id = :did"),
            {"did": debito_id},
        )
        db.execute(
            text(
                """
                INSERT INTO whatsapp_mensagens
                    (adega_id, debito_id, cliente_id, telefone, mensagem,
                     status, message_id, enviado_em)
                VALUES
                    (:adega_id, :debito_id, :cliente_id, :telefone, :mensagem,
                     'enviado', :message_id, NOW())
                """
            ),
            {
                "adega_id": row["adega_id"],
                "debito_id": debito_id,
                "cliente_id": row["cliente_id"],
                "telefone": recipient,
                "mensagem": message,
                "message_id": resultado_baileys.get("message_id"),
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        # não falha o envio por causa disso

    return {
        "ok": True,
        "adega_id": row["adega_id"],
        "telefone": recipient,
        "message_id": resultado_baileys.get("message_id"),
        "jid": resultado_baileys.get("jid"),
    }
