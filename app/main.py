# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import produtos as produtos_router, categorias as categorias_router

# Se as tabelas já existem NO BANCO, isso é "seguro".
# Se quiser, pode comentar depois de criar as tabelas.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API Adega",
    version="1.0.0",
)

# Ajustar conforme seus fronts (local e depois Render)
origins = [
    "http://localhost:3000",        # Next local
    "https://adega-app-api.onrender.com",  # depois você coloca o domínio real aqui
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(produtos_router.router)
app.include_router(categorias_router.router)

@app.get("/")
def read_root():
    return {"message": "API da Adega online"}
