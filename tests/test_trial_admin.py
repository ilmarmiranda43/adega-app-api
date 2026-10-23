
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routers.adegas import (
    conceder_trial,
    prorrogar_trial,
    ativar_assinatura,
)
from app.schemas import TrialConfig, TrialProrrogacao


class FakeDB:
    def __init__(self, adega):
        self.adega = adega
        self.commits = 0

    def execute(self, statement):
        return SimpleNamespace(
            scalar_one_or_none=lambda: self.adega
        )

    def query(self, model):
        return FakeQuery()

    def commit(self):
        self.commits += 1

    def refresh(self, objeto):
        pass

    def rollback(self):
        pass


class FakeQuery:
    def filter(self, *args):
        return self

    def first(self):
        # Nenhum administrador global nesta adega.
        return None


def criar_adega():
    return SimpleNamespace(
        id=2,
        plano="trial",
        status_assinatura="trial",
        trial_inicio=None,
        trial_fim=None,
        trial_dias=None,
    )


def test_conceder_trial_15_dias():
    adega = criar_adega()
    adega.plano = "gratuito"
    adega.status_assinatura = "inativo"

    db = FakeDB(adega)

    resultado = conceder_trial(
        adega_id=2,
        configuracao=TrialConfig(dias=15),
        db=db,
        _usuario=SimpleNamespace(is_platform_admin=True),
    )

    assert resultado["plano"] == "trial"
    assert resultado["trial_dias"] == 15
    assert resultado["status_assinatura"] == "trial"
    assert db.commits == 1

    duracao = adega.trial_fim - adega.trial_inicio
    assert timedelta(days=15) == duracao


def test_prorrogar_trial_10_dias():
    adega = criar_adega()
    adega.trial_inicio = datetime.now(timezone.utc)
    adega.trial_fim = adega.trial_inicio + timedelta(days=15)
    adega.trial_dias = 15

    vencimento_original = adega.trial_fim

    resultado = prorrogar_trial(
        adega_id=2,
        prorrogacao=TrialProrrogacao(dias_adicionais=10),
        db=FakeDB(adega),
        _usuario=SimpleNamespace(is_platform_admin=True),
    )

    assert adega.trial_fim == vencimento_original + timedelta(days=10)
    assert resultado["status_assinatura"] == "trial"


def test_nao_reiniciar_trial_existente():
    adega = criar_adega()
    db = FakeDB(adega)

    with pytest.raises(HTTPException) as erro:
        conceder_trial(
            adega_id=2,
            configuracao=TrialConfig(dias=7),
            db=db,
            _usuario=SimpleNamespace(is_platform_admin=True),
        )

    assert erro.value.status_code == 409
    assert db.commits == 0


def test_ativar_assinatura_paga():
    adega = criar_adega()
    db = FakeDB(adega)

    resultado = ativar_assinatura(
        adega_id=2,
        db=db,
        _usuario=SimpleNamespace(is_platform_admin=True),
    )

    assert resultado["plano"] == "pago"
    assert resultado["status_assinatura"] == "ativo"
    assert db.commits == 1
