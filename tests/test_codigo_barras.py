import os
os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ.setdefault('SECRET_KEY', 'teste')
from types import SimpleNamespace
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base
from app import schemas
from app.routers.produtos import router
from app.deps import get_db_session, require_active_subscription, require_manage_products

def test_fluxo():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, autoflush=False)()
    app = FastAPI(); app.include_router(router)
    usuario = SimpleNamespace(adega_id=1)
    app.dependency_overrides[get_db_session] = lambda: db
    app.dependency_overrides[require_active_subscription] = lambda: usuario
    app.dependency_overrides[require_manage_products] = lambda: usuario
    def dados(codigo):
        return {'nome': 'Teste', 'categoria_id': 1, 'preco': 10, 'codigo_barras': codigo}
    with TestClient(app) as c:
        r = c.post('/produtos/', json=dados('0012345678905'))
        assert r.status_code == 201, r.text
        pid = r.json()['id']
        assert r.json()['codigo_barras'] == '0012345678905'
        assert c.post('/produtos/', json=dados('0012345678905')).status_code == 409
        assert c.get('/produtos/codigo-barras/0012345678905').json()['id'] == pid
        usuario.adega_id = 2
        assert c.get('/produtos/codigo-barras/0012345678905').status_code == 404
        assert c.post('/produtos/', json=dados('0012345678905')).status_code == 201
        usuario.adega_id = 1
        r2 = c.post('/produtos/', json=dados('22222222'))
        assert c.put('/produtos/'+str(r2.json()['id']), json={'codigo_barras': '0012345678905'}).status_code == 409
        assert c.put(f'/produtos/{pid}', json={'ativo': False}).json()['codigo_barras'] == '0012345678905'
        assert c.put(f'/produtos/{pid}', json={'codigo_barras': None}).json()['codigo_barras'] is None
        for codigo in [None, '', '   ']:
            assert c.post('/produtos/', json=dados(codigo)).status_code == 201
        assert c.delete(f'/produtos/{pid}').status_code == 204
    db.close()

@pytest.mark.parametrize('codigo', [12345678, 'a b', 'x'*65, 'abc\nxyz', 'ação'])
def test_invalido(codigo):
    with pytest.raises(ValueError):
        schemas.ProdutoCreate(nome='Teste', categoria_id=1, preco=10, codigo_barras=codigo)
