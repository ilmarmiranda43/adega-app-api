
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.routers.adegas import resposta_trial


def criar_adega_ficticia(status, vencimento, plano="trial"):
    return SimpleNamespace(
        id=999,
        plano=plano,
        status_assinatura=status,
        trial_inicio=datetime.now(timezone.utc),
        trial_fim=vencimento,
        trial_dias=7,
    )


def test_trial_ativo():
    adega = criar_adega_ficticia(
        "trial",
        datetime.now(timezone.utc) + timedelta(days=7),
    )

    resultado = resposta_trial(adega)
    assert resultado["status_assinatura"] == "trial"


def test_trial_expirado():
    adega = criar_adega_ficticia(
        "trial",
        datetime.now(timezone.utc) - timedelta(days=1),
    )

    resultado = resposta_trial(adega)
    assert resultado["status_assinatura"] == "expirado"


def test_assinatura_ativa():
    adega = criar_adega_ficticia(
        "ativo",
        datetime.now(timezone.utc) - timedelta(days=1),
        plano="pago",
    )

    resultado = resposta_trial(adega)
    assert resultado["status_assinatura"] == "ativo"
