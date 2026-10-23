# app/routers/pedidos.py
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_db_session, get_current_user, require_roles



def eh_admin_ou_gerente(usuario) -> bool:
    perfil = getattr(usuario, "perfil", None)

    if perfil is None:
        return False

    if perfil.adega_id != usuario.adega_id:
        return False

    if not perfil.ativo:
        return False

    return bool(perfil.eh_admin or perfil.pode_gerenciar_clientes)



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
    Lista pedidos da ADEGA do usuário logado.

    - Todos os usuários (de qualquer perfil) veem os pedidos da própria adega.
    - status_pedido: filtra pelo status (opcional).
    - cliente_id: filtra por cliente (opcional).
    """

    # Garantir que o usuário está vinculado a uma adega
    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    # Sempre começa filtrando pela adega do usuário logado
    query = db.query(models.Pedido).filter(
        models.Pedido.adega_id == usuario.adega_id
    )

    # Filtro por status (opcional)
    if status_pedido:
        query = query.filter(models.Pedido.status == status_pedido)

    # Filtro por cliente (opcional)
    if cliente_id:
        query = query.filter(models.Pedido.cliente_id == cliente_id)

    pedidos = query.order_by(models.Pedido.id.desc()).all()
    return pedidos


@router.get("/{pedido_id}", response_model=schemas.PedidoRead)
def obter_pedido(
    pedido_id: int,
    db: Session = Depends(get_db_session),
    usuario=Depends(get_current_user),
):
    """
    Busca um pedido da ADEGA do usuário logado.

    - Qualquer usuário logado vê detalhes de pedidos da própria adega.
    - Não mostra pedidos de outras adegas.
    """

    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    pedido = (
        db.query(models.Pedido)
        .filter(
            models.Pedido.id == pedido_id,
            models.Pedido.adega_id == usuario.adega_id,
        )
        .first()
    )
    if not pedido:
        # Pode ser que não exista ou não pertença à adega do usuário
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    # OBS: aqui removi a restrição por cliente_id, para ficar consistente
    # com o listar_pedidos (todo mundo da adega enxerga os pedidos da adega).

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
    Cria pedido SEMPRE na adega do usuário logado.

    - Admin/Gerente podem criar pedido para qualquer cliente.
    - Outros: se tiverem cliente_id associado, o pedido é forçado para ele.
    """

    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    if not eh_admin_ou_gerente(usuario) and getattr(usuario, "cliente_id", None):
        cliente_id = usuario.cliente_id
    else:
        cliente_id = pedido_in.cliente_id

    # Validar se o cliente pertence à mesma adega
    if cliente_id is not None:
        cliente = (
            db.query(models.Cliente)
            .filter(
                models.Cliente.id == cliente_id,
                models.Cliente.adega_id == usuario.adega_id,
            )
            .first()
        )

        if cliente is None:
            raise HTTPException(
                status_code=404,
                detail="Cliente não encontrado nesta adega.",
            )


    pedido = models.Pedido(
        cliente_id=cliente_id,
        usuario_id=usuario.id,
        observacoes=pedido_in.observacoes,
        status="aberto",
        adega_id=usuario.adega_id,  # sempre da adega do usuário
    )

    total = 0

    for item_in in pedido_in.itens:
        produto = (
            db.query(models.Produto)
            .filter(
                models.Produto.id == item_in.produto_id,
                models.Produto.adega_id == usuario.adega_id,
            )
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
            total_liquido=subtotal,  # aqui faz mais sentido por item
        )

        pedido.itens.append(item)

    pedido.valor_liquido = total
    pedido.valor_bruto = total  # se você usar desconto depois, já deixa pronto
    pedido.desconto_total = 0

    db.add(pedido)
    db.commit()
    db.refresh(pedido)
    return pedido


@router.put("/{pedido_id}/status", response_model=schemas.PedidoRead)
def atualizar_status_pedido(
    pedido_id: int,
    novo_status: str,
    db: Session = Depends(get_db_session),
    usuario=Depends(get_current_user),
):
    """
    Atualiza o status de um pedido da ADEGA do usuário logado.

    - (opcional) pode manter restrição só para admin/gerente.
    """

    if novo_status not in ("aberto", "confirmado", "cancelado"):
        raise HTTPException(status_code=400, detail="Status inválido")

    if not hasattr(usuario, "adega_id") or usuario.adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário não está vinculado a nenhuma adega.",
        )

    # Se quiser que só admin/gerente alterem status, descomente:
    if not eh_admin_ou_gerente(usuario):
        raise HTTPException(
            status_code=403,
            detail="Sem permissão para alterar status de pedidos.",
        )

    pedido = (
        db.query(models.Pedido)
        .filter(
            models.Pedido.id == pedido_id,
            models.Pedido.adega_id == usuario.adega_id,
        )
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    status_anterior = pedido.status

    if status_anterior == "confirmado" and novo_status != "confirmado":
        raise HTTPException(
            status_code=409,
            detail=(
                "Pedido confirmado não pode retornar para aberto "
                "ou cancelado sem estorno de estoque."
            ),
        )

    # Se vamos confirmar agora e antes não era confirmado, baixa estoque
    if novo_status == "confirmado" and status_anterior != "confirmado":
        for item in pedido.itens:
            # Estoque da MESMA adega
            estoque = (
                db.query(models.Estoque)
                .filter(
                    models.Estoque.produto_id == item.produto_id,
                    models.Estoque.adega_id == usuario.adega_id,  # <-- ajuste aqui
                )
                .first()
            )
            if not estoque:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Produto {item.produto_id} não possui registro "
                        f"de estoque para esta adega"
                    ),
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
                .filter(
                    models.Estoque.produto_id == item.produto_id,
                    models.Estoque.adega_id == usuario.adega_id,
                )
                .first()
            )
            estoque.quantidade -= item.quantidade

    pedido.status = novo_status
    db.commit()
    db.refresh(pedido)
    return pedido
