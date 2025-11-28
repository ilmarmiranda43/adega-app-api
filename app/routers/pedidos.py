from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from .. import models, schemas
from ..dependencies import get_current_user  # ajuste para o seu projeto

def eh_admin_ou_gerente(usuario) -> bool:
    """
    Retorna True se o usuário for administrador ou gerente.
    Ajuste os nomes/IDs conforme sua tabela de perfis.
    """
    # 1) Tenta pelo relacionamento perfil.nome
    try:
        perfil = getattr(usuario, "perfil", None)
        if perfil is not None and getattr(perfil, "nome", None):
            nome = perfil.nome.strip().lower()
            if nome in ("administrador", "admin", "gerente"):
                return True
    except Exception:
        pass

    # 2) Fallback por ID de perfil (ajuste se for diferente)
    perfil_id = getattr(usuario, "perfil_id", None)
    if perfil_id in (1, 2):  # 1 = admin, 2 = gerente (exemplo)
        return True

    return False


router = APIRouter(
    prefix="/pedidos",
    tags=["pedidos"],
)


@router.get("/", response_model=List[schemas.PedidoRead])
def listar_pedidos(
    status_pedido: Optional[str] = None,
    cliente_id: Optional[int] = None,
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user),
):
    query = db.query(models.Pedido)

    if status_pedido:
        query = query.filter(models.Pedido.status == status_pedido)

    if cliente_id:
        query = query.filter(models.Pedido.cliente_id == cliente_id)

    # regra de permissão: se NÃO for admin/gerente, só vê pedidos do próprio cliente
    if not eh_admin_ou_gerente(usuario):
        # se você tiver usuario.cliente_id:
        if hasattr(usuario, "cliente_id") and usuario.cliente_id:
            query = query.filter(models.Pedido.cliente_id == usuario.cliente_id)
        else:
            # se não tiver cliente_id associado, não retorna nada
            query = query.filter(models.Pedido.cliente_id == -1)

    pedidos = query.order_by(models.Pedido.id.desc()).all()
    return pedidos




@router.get("/{pedido_id}", response_model=schemas.PedidoRead)
def obter_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user),
):
    pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    if usuario.role not in ("admin", "gerente") and pedido.cliente_id != usuario.cliente_id:
        raise HTTPException(status_code=403, detail="Sem permissão para visualizar este pedido")

    return pedido


@router.post("/", response_model=schemas.PedidoRead, status_code=status.HTTP_201_CREATED)
def criar_pedido(
    pedido_in: schemas.PedidoCreate,
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user),
):
    # se for cliente, força usar o cliente_id dele (se tiver essa relação)
    # se não for admin/gerente e tiver cliente_id, força usar o cliente_id do usuário
    if not eh_admin_ou_gerente(usuario) and getattr(usuario, "cliente_id", None):
        cliente_id = usuario.cliente_id
    else:
        cliente_id = pedido_in.cliente_id


    # cria objeto Pedido
    pedido = models.Pedido(
        cliente_id=cliente_id,
        observacoes=pedido_in.observacoes,
        status="aberto",
    )

    total = 0

    for item_in in pedido_in.itens:
        produto = db.query(models.Produto).filter(models.Produto.id == item_in.produto_id).first()
        if not produto:
            raise HTTPException(status_code=400, detail=f"Produto {item_in.produto_id} não encontrado")

        preco_unitario = produto.preco_venda  # ajuste para o nome do campo de preço
        subtotal = preco_unitario * item_in.quantidade

        total += subtotal

        item = models.ItemPedido(
            produto_id=item_in.produto_id,
            quantidade=item_in.quantidade,
            preco_unitario=preco_unitario,
            # subtotal=subtotal,
        )

        pedido.itens.append(item)
        # total += subtotal

    pedido.valor_total  = subtotal
    db.add(pedido)
    db.commit()
    db.refresh(pedido)
    return pedido


@router.put("/{pedido_id}/status", response_model=schemas.PedidoRead)
def atualizar_status_pedido(
    pedido_id: int,
    novo_status: str,
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user),
):
    if novo_status not in ("aberto", "confirmado", "cancelado"):
        raise HTTPException(status_code=400, detail="Status inválido")

    if not eh_admin_ou_gerente(usuario):
        raise HTTPException(
        status_code=403,
        detail="Somente admin/gerente podem alterar status"
    )


    pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    status_anterior = pedido.status

    # Se vamos confirmar agora e antes não era confirmado, baixa estoque
    if novo_status == "confirmado" and status_anterior != "confirmado":
        # 1) Verificar se tem estoque
        for item in pedido.itens:
            estoque = (
                db.query(models.Estoque)
                .filter(models.Estoque.produto_id == item.produto_id)
                .first()
            )
            if not estoque:
                raise HTTPException(
                    status_code=400,
                    detail=f"Produto {item.produto_id} não possui registro de estoque"
                )

            if estoque.quantidade < item.quantidade:
                raise HTTPException(
                    status_code=400,
                    detail=f"Estoque insuficiente para o produto {item.produto_id}. Disponível: {estoque.quantidade}, necessário: {item.quantidade}"
                )

        # 2) Dar baixa
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

