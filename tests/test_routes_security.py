
import os

# Deve ser configurado ANTES de importar app.main.
# Banco SQLite temporário, independente do PostgreSQL.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ.setdefault("SECRET_KEY", "chave-local-apenas-para-testes")

from fastapi.routing import APIRoute
from app.main import app


def obter_dependencias(rota):
    nomes = set()

    def percorrer(dependencia):
        if dependencia.call is not None:
            nomes.add(
                getattr(dependencia.call, "__name__", "")
            )

        for sub in dependencia.dependencies:
            percorrer(sub)

    percorrer(rota.dependant)
    return nomes


def test_rotas_comerciais_protegidas():
    prefixos = (
        "/pedidos",
        "/produtos",
        "/categorias",
        "/estoque",
        "/clientes",
        "/usuarios",
    )

    rotas = [
        rota for rota in app.routes
        if isinstance(rota, APIRoute)
        and rota.path.startswith(prefixos)
    ]

    assert rotas, "Nenhuma rota comercial encontrada."

    for rota in rotas:
        dependencias = obter_dependencias(rota)

        assert "require_active_subscription" in dependencias, (
            f"Rota sem validação de assinatura: "
            f"{rota.path} {rota.methods}"
        )


def test_rotas_administrativas_protegidas():
    prefixos = ("/adegas", "/perfis")

    rotas = [
        rota for rota in app.routes
        if isinstance(rota, APIRoute)
        and rota.path.startswith(prefixos)
    ]

    assert rotas, "Nenhuma rota administrativa encontrada."

    for rota in rotas:
        dependencias = obter_dependencias(rota)

        assert "require_platform_admin" in dependencias, (
            f"Rota administrativa sem proteção: "
            f"{rota.path} {rota.methods}"
        )
