# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import produtos as produtos_router, categorias as categorias_router, auth as auth_router, perfis, usuarios,clientes, estoque, pedidos, adegas, perfis_master

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
    "http://127.0.0.1:3000",        # Next local
    "https://adega-app-api.onrender.com", 
     "https://adega-app-zeta.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
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
    perfis_master.router,
]

for r in routers:
    app.include_router(r)



@app.get("/")
def read_root():
    return {"message": "API da Adega online"}
