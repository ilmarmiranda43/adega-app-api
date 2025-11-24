# app/security.py
from passlib.context import CryptContext

# UM ÚNICO contexto, usado para hash e verify
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def get_password_hash(password: str) -> str:
    """
    Gera o hash bcrypt da senha em texto puro.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compara a senha em texto puro com o hash armazenado no banco.
    """
    return pwd_context.verify(plain_password, hashed_password)
