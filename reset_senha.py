from getpass import getpass

from app.database import SessionLocal
from app.models import Usuario
from app.security import get_password_hash


email = input("E-mail do usuário: ").strip().lower()
nova_senha = getpass("Nova senha: ")
confirmacao = getpass("Confirme a nova senha: ")

if nova_senha != confirmacao:
    raise SystemExit("As senhas não são iguais.")

if len(nova_senha) < 6:
    raise SystemExit("A senha precisa ter pelo menos 6 caracteres.")

if len(nova_senha.encode("utf-8")) > 72:
    raise SystemExit("A senha ultrapassa o limite do bcrypt.")

db = SessionLocal()

try:
    usuario = (
        db.query(Usuario)
        .filter(Usuario.email == email)
        .first()
    )

    if not usuario:
        raise SystemExit("Usuário não encontrado.")

    usuario.senha_hash = get_password_hash(nova_senha)
    db.commit()

    print(f"Senha redefinida com sucesso para: {usuario.email}")

except Exception:
    db.rollback()
    raise

finally:
    db.close()