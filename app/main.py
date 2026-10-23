# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import produtos as produtos_router, categorias as categorias_router, auth as auth_router, perfis, usuarios,clientes, estoque, pedidos, adegas, debitos

import os

APP_ENV = os.getenv("APP_ENV", "production").lower()
IS_HOMOLOGACAO = APP_ENV == "homologacao"

# Se as tabelas já existem NO BANCO, isso é "seguro".
# Se quiser, pode comentar depois de criar as tabelas.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API Adega",
    version="1.0.0",
)

# Ajustar conforme seus fronts (local e depois Render)
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://adega-app.onrender.com",
    "https://adega-app-api.onrender.com",
    "https://demo.imbebitec.com.br/",
]

if IS_HOMOLOGACAO:
    origins.append("https://demo.imbebitec.com.br/")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


routers = [
        produtos_router.router,
        categorias_router.router,
        auth_router.router,
        perfis.router,
        usuarios.router,
        clientes.router,
        estoque.router,
        pedidos.router,
        adegas.router,
    ]

# Módulo de débitos habilitado somente fora da homologação
if not IS_HOMOLOGACAO:
    routers.append(debitos.router)

for r in routers:
    app.include_router(r)

@app.get("/")
def read_root():
    return {"message": "API da Adega online"}
