# app/routers/pedidos.py
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_db_session, get_current_user, require_roles


def eh_admin_ou_gerente(usuario) -> bool:
    """
    Retorna True se o usuário for administrador ou gerente.
    Usa perfil_id (1, 2) como base.
    """
    perfil_id = getattr(usuario, "perfil_id", None)
    return perfil_id in (1, 2)


router = APIRouter(
    prefix="/pedidos",
    tags=["Pedidos"],
)


@router.get("/", response_model=List[schemas.PedidoResponse])
def listar_pedidos(
    status_pedido: Optional[str] = None,
    cliente_id: Optional[int] = None,
    db: Session = Depends(get_db_session),
    usuario=Depends(get_current_user),
):
    """
    - Admin/Gerente: vê todos os pedidos (com filtros opcionais).
    - Outros: podem ver apenas pedidos do próprio cliente_id (se existir).
    """
    query = db.query(models.Pedido)

    if status_pedido:
        query = query.filter(models.Pedido.status == status_pedido)

    if cliente_id:
        query = query.filter(models.Pedido.cliente_id == cliente_id)

    if not eh_admin_ou_gerente(usuario):
        # se o usuário tiver cliente_id associado, filtra por ele
        if hasattr(usuario, "cliente_id") and usuario.cliente_id:
            query = query.filter(models.Pedido.cliente_id == usuario.cliente_id)
        else:
            # sem cliente_id associado → não vê nada
            query = query.filter(models.Pedido.cliente_id == -1)

    pedidos = query.order_by(models.Pedido.id.desc()).all()
    return pedidos


@router.get("/{pedido_id}", response_model=schemas.PedidoRead)
def obter_pedido(
    pedido_id: int,
    db: Session = Depends(get_db_session),
    usuario=Depends(get_current_user),
):
    pedido = (
        db.query(models.Pedido)
        .filter(models.Pedido.id == pedido_id)
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    if not eh_admin_ou_gerente(usuario):
        if pedido.cliente_id != getattr(usuario, "cliente_id", None):
            raise HTTPException(
                status_code=403,
                detail="Sem permissão para visualizar este pedido",
            )

    return pedido


@router.post(
    "/",
    response_model=schemas.PedidoRead,
    status_code=status.HTTP_201_CREATED,
)
def criar_pedido(
    pedido_in: schemas.PedidoCreate,
    db: Session = Depends(get_db_session),
    usuario: models.Usuario = Depends(get_current_user),
):
    """
    - Admin/Gerente podem criar pedido para qualquer cliente.
    - Outros: se tiverem cliente_id associado, o pedido é forçado para ele.
    """
    if not eh_admin_ou_gerente(usuario) and getattr(usuario, "cliente_id", None):
        cliente_id = usuario.cliente_id
    else:
        cliente_id = pedido_in.cliente_id

    pedido = models.Pedido(
        cliente_id=cliente_id,
        observacoes=pedido_in.observacoes,
        status="aberto",
        adega_id=usuario.adega_id,
    )

    total = 0

    for item_in in pedido_in.itens:
        produto = (
            db.query(models.Produto)
            .filter(models.Produto.id == item_in.produto_id)
            .first()
        )
        if not produto:
            raise HTTPException(
                status_code=400,
                detail=f"Produto {item_in.produto_id} não encontrado",
            )

        preco_unitario = produto.preco
        subtotal = preco_unitario * item_in.quantidade
        total += subtotal

        item = models.ItemPedido(
            produto_id=item_in.produto_id,
            quantidade=item_in.quantidade,
            preco_unitario=preco_unitario,
            desconto=0,
            total_liquido=total,
        )

        pedido.itens.append(item)

    pedido.valor_liquido = total

    db.add(pedido)
    db.commit()
    db.refresh(pedido)
    return pedido


@router.put("/{pedido_id}/status", response_model=schemas.PedidoRead)
def atualizar_status_pedido(
    pedido_id: int,
    novo_status: str,
    db: Session = Depends(get_db_session),
    _usuario=Depends(require_roles([1, 2])),  # só admin/gerente
):
    if novo_status not in ("aberto", "confirmado", "cancelado"):
        raise HTTPException(status_code=400, detail="Status inválido")

    pedido = (
        db.query(models.Pedido)
        .filter(models.Pedido.id == pedido_id)
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    status_anterior = pedido.status

    # Se vamos confirmar agora e antes não era confirmado, baixa estoque
    if novo_status == "confirmado" and status_anterior != "confirmado":
        for item in pedido.itens:
            estoque = (
                db.query(models.Estoque)
                .filter(models.Estoque.produto_id == item.produto_id)
                .first()
            )
            if not estoque:
                raise HTTPException(
                    status_code=400,
                    detail=f"Produto {item.produto_id} não possui registro de estoque",
                )

            if estoque.quantidade < item.quantidade:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Estoque insuficiente para o produto {item.produto_id}. "
                        f"Disponível: {estoque.quantidade}, necessário: {item.quantidade}"
                    ),
                )

        # baixa estoque
        for item in pedido.itens:
            estoque = (
                db.query(models.Estoque)
                .filter(models.Estoque.produto_id == item.produto_id)
                .first()
            )
            estoque.quantidade -= item.quantidade

    pedido.status = novo_status
    db.commit()
    db.refresh(pedido)
    return pedido
