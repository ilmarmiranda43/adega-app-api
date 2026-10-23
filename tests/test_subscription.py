
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.deps import require_active_subscription


class FakeQuery:
    def __init__(self, adega):
        self.adega = adega

    def filter(self, *args):
        return self

    def first(self):
        return self.adega


class FakeDB:
    def __init__(self, adega):
        self.adega = adega

    def query(self, model):
        return FakeQuery(self.adega)


def criar_usuario(perfil_id=3):
    return SimpleNamespace(
        id=1,
        adega_id=2,
        perfil_id=perfil_id,
    )


def criar_adega(plano, status, vencimento=None):
    return SimpleNamespace(
        id=2,
        plano=plano,
        status_assinatura=status,
        trial_fim=vencimento,
    )


def test_trial_valido():
    adega = criar_adega(
        "trial",
        "trial",
        datetime.now(timezone.utc) + timedelta(days=7),
    )

    usuario = criar_usuario()

    resultado = require_active_subscription(
        usuario=usuario,
        db=FakeDB(adega),
    )

    assert resultado is usuario


def test_trial_expirado():
    adega = criar_adega(
        "trial",
        "trial",
        datetime.now(timezone.utc) - timedelta(days=1),
    )

    with pytest.raises(HTTPException) as erro:
        require_active_subscription(
            usuario=criar_usuario(),
            db=FakeDB(adega),
        )

    assert erro.value.status_code == 403


def test_assinatura_ativa():
    adega = criar_adega("pago", "ativo")

    usuario = criar_usuario()

    resultado = require_active_subscription(
        usuario=usuario,
        db=FakeDB(adega),
    )

    assert resultado is usuario


def test_assinatura_suspensa():
    adega = criar_adega("pago", "suspenso")

    with pytest.raises(HTTPException) as erro:
        require_active_subscription(
            usuario=criar_usuario(),
            db=FakeDB(adega),
        )

    assert erro.value.status_code == 403


from app.deps import require_manage_products


def test_gerente_pode_gerenciar_produtos():
    usuario = criar_usuario()

    perfil = SimpleNamespace(
        id=3,
        adega_id=2,
        ativo=True,
        eh_admin=False,
        pode_gerenciar_estoque=True,
    )

    resultado = require_manage_products(
        usuario=usuario,
        db=FakeDB(perfil),
    )

    assert resultado is usuario


def test_usuario_sem_permissao():
    usuario = criar_usuario(perfil_id=4)

    perfil = SimpleNamespace(
        id=4,
        adega_id=2,
        ativo=True,
        eh_admin=False,
        pode_gerenciar_estoque=False,
    )

    with pytest.raises(HTTPException) as erro:
        require_manage_products(
            usuario=usuario,
            db=FakeDB(perfil),
        )

    assert erro.value.status_code == 403


def test_perfil_inexistente():
    with pytest.raises(HTTPException) as erro:
        require_manage_products(
            usuario=criar_usuario(),
            db=FakeDB(None),
        )

    assert erro.value.status_code == 403
