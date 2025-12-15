# app/routers/debitos.py
import re
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from ..schemas import DebitoCreate, DebitoOut, EnviarWhatsAppIn
from app.security import get_current_user  # ajuste para o seu projeto

router = APIRouter(prefix="/debitos", tags=["Débitos"])

def so_digitos(phone: str) -> str:
    return re.sub(r"\D+", "", phone or "")

@router.post("/", response_model=DebitoOut)
def criar_debito(
    payload: DebitoCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    # TODO: aplique sua regra de permissão (admin/master)
    # if not user.pode_gerenciar_clientes: ...

    # Valida cliente pertence à adega (boa prática multi-tenant)
    cliente = db.execute(
        """
        SELECT id, telefone, eh_whatsapp
        FROM clientes
        WHERE id = :cid AND adega_id = :aid
        """,
        {"cid": payload.cliente_id, "aid": payload.adega_id},
    ).mappings().first()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado para esta adega.")

    debito = db.execute(
        """
        INSERT INTO debitos_clientes (adega_id, cliente_id, valor, descricao, vencimento)
        VALUES (:aid, :cid, :valor, :descricao, :vencimento)
        RETURNING id, adega_id, cliente_id, valor, descricao, status, vencimento, criado_em
        """,
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
    SELECT id, adega_id, cliente_id, valor, descricao, status, vencimento, criado_em
    FROM debitos_clientes
    WHERE adega_id = :aid
    """
    params = {"aid": adega_id}

    if status:
        q += " AND status = :status"
        params["status"] = status

    q += " ORDER BY criado_em DESC"

    rows = db.execute(q, params).mappings().all()
    return rows

@router.post("/{debito_id}/enviar-whatsapp")
async def enviar_whatsapp_debito(
    debito_id: int,
    body: EnviarWhatsAppIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    # Busca débito + cliente + api key da adega
    row = db.execute(
        """
        SELECT d.id, d.adega_id, d.valor, d.descricao, d.vencimento, d.status,
               c.nome as cliente_nome, c.telefone, c.eh_whatsapp,
               a.textmebot_api_key
        FROM debitos_clientes d
        JOIN clientes c ON c.id = d.cliente_id
        JOIN adegas a ON a.id = d.adega_id
        WHERE d.id = :did
        """,
        {"did": debito_id},
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Débito não encontrado.")

    if row["status"] != "aberto":
        raise HTTPException(status_code=400, detail="Só é possível enviar WhatsApp para débito em aberto.")

    if not row["textmebot_api_key"]:
        raise HTTPException(status_code=400, detail="Esta adega não possui textmebot_api_key configurada.")

    if not row["telefone"]:
        raise HTTPException(status_code=400, detail="Cliente sem telefone cadastrado.")

    if row.get("eh_whatsapp") is False:
        raise HTTPException(status_code=400, detail="Cliente marcado como não-WhatsApp.")

    recipient = so_digitos(row["telefone"])
    if not recipient.startswith("55"):
        # se você sempre usa Brasil, pode forçar 55
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
            f"Consta um débito em aberto na adega.\n\n"
            f"• Valor: R$ {valor}\n"
            f"• Vencimento: {venc}\n"
            f"• Descrição: {desc}\n\n"
            f"Se precisar, me chame por aqui."
        )

    # TextMeBot: GET send.php com recipient/apikey/text :contentReference[oaicite:1]{index=1}
    url = "https://api.textmebot.com/send.php"
    params = {
        "recipient": recipient,
        "text": message,
        "apikey": row["textmebot_api_key"],
        "json": "yes",   # opcional (se suportado na sua conta)
    }

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(url, params=params)

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Falha ao enviar WhatsApp (HTTP {resp.status_code}).")

    # Se vier JSON, devolve para o front
    return {"ok": True, "textmebot_response": resp.text}
