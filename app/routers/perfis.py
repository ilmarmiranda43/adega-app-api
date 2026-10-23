# app/routers/perfis.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..deps import get_db_session, require_platform_admin
from .. import models, schemas

router = APIRouter(
    prefix="/perfis",
    tags=["Perfis"],
)

# Mapeamento lógico de tipos de perfil
TIPOS_PERFIL = {
    1: "Admin",
    2: "Gerente",
    3: "Usuário",
}
NOME_PARA_TIPO_ID = {v: k for k, v in TIPOS_PERFIL.items()}


@router.get("/", response_model=list[schemas.PerfilOut])
def listar_perfis(
    adega_id: int | None = None,
    incluir_inativos: bool = False,
    db: Session = Depends(get_db_session),
    # Somente MASTER pode listar perfis
    usuario=Depends(require_platform_admin),
):
    """
    Lista perfis de uma ADEGA específica.

    Regras:
    - Somente o usuário MASTER pode listar perfis.
    - É obrigatório informar o adega_id (adega selecionada no frontend).
    - Por padrão traz apenas perfis ativos.
      Use ?incluir_inativos=true para trazer todos.
    """
    if adega_id is None:
        raise HTTPException(
            status_code=400,
            detail="Informe o adega_id para listar os perfis da adega selecionada.",
        )

    adega = db.query(models.Adega).filter(models.Adega.id == adega_id).first()
    if not adega:
        raise HTTPException(
            status_code=404,
            detail="A adega informada não existe.",
        )

    query = db.query(models.Perfil).filter(models.Perfil.adega_id == adega_id)

    if not incluir_inativos:
        query = query.filter(models.Perfil.ativo == True)  # noqa: E712

    perfis = query.order_by(models.Perfil.nome).all()
    return perfis


@router.post(
    "/",
    response_model=schemas.PerfilOut,
    status_code=status.HTTP_201_CREATED,
)
def criar_perfil(
    perfil_in: schemas.PerfilBase,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_platform_admin),  # Somente MASTER
):
    """
    Cria um perfil para a ADEGA enviada no body da requisição.

    Regras:
    - Só o MASTER pode criar perfis.
    - Em cada adega só pode existir UM perfil de cada tipo:
        "Admin", "Gerente", "Usuário"
    - O tipo é determinado pelo nome enviado.
    - O adega_id vem da requisição e NÃO do usuário logado.
    """

    # 1. Validar nome do perfil
    nome_normalizado = perfil_in.nome.strip()
    tipo_id = NOME_PARA_TIPO_ID.get(nome_normalizado)
    if tipo_id is None:
        raise HTTPException(
            status_code=400,
            detail='Tipo de perfil inválido. Use "Admin", "Gerente" ou "Usuário".',
        )

    # 2. Validar se existe a adega
    adega = db.query(models.Adega).filter(models.Adega.id == perfil_in.adega_id).first()
    if not adega:
        raise HTTPException(status_code=404, detail="A adega informada não existe.")

    # 3. Verificar se já existe perfil com esse nome nessa adega
    existente = (
        db.query(models.Perfil)
        .filter(
            models.Perfil.adega_id == perfil_in.adega_id,
            models.Perfil.nome == nome_normalizado,
        )
        .first()
    )
    if existente:
        raise HTTPException(
            status_code=400,
            detail="Já existe um perfil desse tipo nesta adega.",
        )

    # 4. Criar o perfil usando o adega_id enviado
    perfil = models.Perfil(
        adega_id=perfil_in.adega_id,
        nome=nome_normalizado,
        descricao=perfil_in.descricao,
        eh_admin=getattr(perfil_in, "eh_admin", False),
        pode_gerenciar_usuarios=getattr(perfil_in, "pode_gerenciar_usuarios", False),
        pode_gerenciar_estoque=getattr(perfil_in, "pode_gerenciar_estoque", False),
        pode_gerenciar_clientes=getattr(perfil_in, "pode_gerenciar_clientes", False),
        ativo=True,
    )

    db.add(perfil)
    db.commit()
    db.refresh(perfil)

    return perfil


@router.put("/{perfil_id}", response_model=schemas.PerfilOut)
def atualizar_perfil(
    perfil_id: int,
    perfil_in: schemas.PerfilBase,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_platform_admin),  # Somente MASTER
):
    """
    Atualiza um perfil de uma ADEGA específica.

    Regras:
    - Somente o MASTER pode atualizar perfis.
    - O adega_id vem do body (adega selecionada no frontend).
    - Mantém a regra de não permitir dois perfis com o mesmo nome na mesma adega.
    """

    # 1. Validar nome e tipo
    nome_normalizado = perfil_in.nome.strip()
    tipo_id = NOME_PARA_TIPO_ID.get(nome_normalizado)
    if tipo_id is None:
        raise HTTPException(
            status_code=400,
            detail='Tipo de perfil inválido. Use "Admin", "Gerente" ou "Usuário".',
        )

    # 2. Validar adega
    adega = db.query(models.Adega).filter(models.Adega.id == perfil_in.adega_id).first()
    if not adega:
        raise HTTPException(status_code=404, detail="A adega informada não existe.")

    # 3. Buscar perfil pelo id e adega selecionada
    perfil = (
        db.query(models.Perfil)
        .filter(
            models.Perfil.id == perfil_id,
            models.Perfil.adega_id == perfil_in.adega_id,
        )
        .first()
    )
    if not perfil:
        raise HTTPException(
            status_code=404,
            detail="Perfil não encontrado para a adega informada.",
        )

    # 4. Verificar se já existe outro perfil com o mesmo nome nessa adega
    existente = (
        db.query(models.Perfil)
        .filter(
            models.Perfil.adega_id == perfil_in.adega_id,
            models.Perfil.nome == nome_normalizado,
            models.Perfil.id != perfil_id,
        )
        .first()
    )
    if existente:
        raise HTTPException(
            status_code=400,
            detail="Já existe outro perfil com esse nome nesta adega.",
        )

    # 5. Atualizar dados do perfil
    perfil.nome = nome_normalizado
    perfil.descricao = perfil_in.descricao
    perfil.eh_admin = getattr(perfil_in, "eh_admin", perfil.eh_admin)
    perfil.pode_gerenciar_usuarios = getattr(
        perfil_in,
        "pode_gerenciar_usuarios",
        perfil.pode_gerenciar_usuarios,
    )
    perfil.pode_gerenciar_estoque = getattr(
        perfil_in,
        "pode_gerenciar_estoque",
        perfil.pode_gerenciar_estoque,
    )
    perfil.pode_gerenciar_clientes = getattr(
        perfil_in,
        "pode_gerenciar_clientes",
        perfil.pode_gerenciar_clientes,
    )
    # Não mexo em "ativo" aqui, isso é responsabilidade das rotas de ativar/inativar

    db.commit()
    db.refresh(perfil)

    return perfil


@router.patch("/{perfil_id}/ativar", response_model=schemas.PerfilOut)
def ativar_perfil(
    perfil_id: int,
    adega_id: int,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_platform_admin),  # Somente MASTER
):
    """
    Ativa um perfil de acordo com a ADEGA selecionada.

    Regras:
    - Somente o MASTER pode ativar perfis.
    - O adega_id vem da query string (?adega_id=).
    """

    adega = db.query(models.Adega).filter(models.Adega.id == adega_id).first()
    if not adega:
        raise HTTPException(
            status_code=404,
            detail="A adega informada não existe.",
        )

    perfil = (
        db.query(models.Perfil)
        .filter(
            models.Perfil.id == perfil_id,
            models.Perfil.adega_id == adega_id,
        )
        .first()
    )
    if not perfil:
        raise HTTPException(
            status_code=404,
            detail="Perfil não encontrado para a adega informada.",
        )

    perfil.ativo = True
    db.commit()
    db.refresh(perfil)
    return perfil


@router.patch("/{perfil_id}/inativar", response_model=schemas.PerfilOut)
def inativar_perfil(
    perfil_id: int,
    adega_id: int,
    db: Session = Depends(get_db_session),
    usuario=Depends(require_platform_admin),  # Somente MASTER
):
    """
    Inativa um perfil de acordo com a ADEGA selecionada.

    Regras:
    - Somente o MASTER pode inativar perfis.
    - O adega_id vem da query string (?adega_id=).
    """

    adega = db.query(models.Adega).filter(models.Adega.id == adega_id).first()
    if not adega:
        raise HTTPException(
            status_code=404,
            detail="A adega informada não existe.",
        )

    perfil = (
        db.query(models.Perfil)
        .filter(
            models.Perfil.id == perfil_id,
            models.Perfil.adega_id == adega_id,
        )
        .first()
    )
    if not perfil:
        raise HTTPException(
            status_code=404,
            detail="Perfil não encontrado para a adega informada.",
        )

    perfil.ativo = False
    db.commit()
    db.refresh(perfil)
    return perfil
