
import os
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite://"
os.environ.setdefault("SECRET_KEY", "chave-local-apenas-para-testes")

from fastapi.testclient import TestClient

# Evita que o app.main execute create_all durante a importação.
with patch("app.database.Base.metadata.create_all"):
    from app.main import app


client = TestClient(app)


def test_produtos_sem_token():
    resposta = client.get("/produtos/")
    assert resposta.status_code in (401, 403)


def test_clientes_sem_token():
    resposta = client.get("/clientes/")
    assert resposta.status_code in (401, 403)


def test_trial_sem_token():
    resposta = client.get("/adegas/2/trial")
    assert resposta.status_code in (401, 403)


def test_perfis_sem_token():
    resposta = client.get("/perfis/?adega_id=2")
    assert resposta.status_code in (401, 403)


from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.deps import (
    get_current_user,
    get_db_session,
    require_active_subscription,
)



class FakeQuery:
    def __init__(self, adega):
        self.adega = adega

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def first(self):
        return self.adega

    def all(self):
        return []



class FakeDB:
    def __init__(self, adega):
        self.adega = adega

    def query(self, model):
        return FakeQuery(self.adega)


def criar_adega_teste(dias):
    return SimpleNamespace(
        id=2,
        plano="trial",
        status_assinatura="trial",
        trial_fim=datetime.now(timezone.utc)
        + timedelta(days=dias),
    )


def configurar_usuario_teste(adega):
    usuario = SimpleNamespace(
        id=10,
        adega_id=2,
        perfil_id=3,
        is_platform_admin=False,
    )

    app.dependency_overrides[get_current_user] = lambda: usuario
    app.dependency_overrides[get_db_session] = lambda: FakeDB(adega)


def limpar_dependencias():
    app.dependency_overrides.clear()


def test_trial_valido_acesso():
    configurar_usuario_teste(criar_adega_teste(7))

    try:
        resposta = client.get("/produtos/")
        assert resposta.status_code == 200
    finally:
        limpar_dependencias()


def test_trial_expirado_bloqueado():
    configurar_usuario_teste(criar_adega_teste(-1))

    try:
        resposta = client.get("/produtos/")
        assert resposta.status_code == 403
    finally:
        limpar_dependencias()
