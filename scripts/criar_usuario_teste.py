
import getpass

from sqlalchemy import select, text

from app.database import SessionLocal
from app.models import Adega, Perfil, Usuario
from app.security import get_password_hash


BANCO_ESPERADO = "adegas_teste"
ADEGA_ID = 3
PERFIL_ID = 2


def criar_usuario_teste():
    print("\n=== USUÁRIO DE HOMOLOGAÇÃO ===")

    # Verifica o banco ANTES de solicitar
    # informações e realizar alterações.
    with SessionLocal.begin() as db:

        banco_atual = db.execute(
            text("SELECT current_database()")
        ).scalar_one()

        print(f"Banco conectado: {banco_atual}")

        if banco_atual != BANCO_ESPERADO:
            raise RuntimeError(
                "Banco incorreto! Operação cancelada."
            )

        adega = db.execute(
            select(Adega).where(Adega.id == ADEGA_ID)
        ).scalar_one_or_none()

        if adega is None:
            raise RuntimeError(
                "Adega de teste não encontrada."
            )

        if adega.nome != "Adega Teste Vencimento":
            raise RuntimeError(
                "O ID 3 não corresponde à adega esperada."
            )

        perfil = db.execute(
            select(Perfil).where(
                Perfil.id == PERFIL_ID,
                Perfil.adega_id == ADEGA_ID,
                Perfil.ativo.is_(True),
            )
        ).scalar_one_or_none()

        if perfil is None:
            print("\nPerfis cadastrados para a adega 3:")

            perfis = db.execute(
                select(Perfil).where(
                    Perfil.adega_id == ADEGA_ID
                )
            ).scalars().all()

            for p in perfis:
                print(
                    f"ID: {p.id} | "
                    f"Nome: {p.nome} | "
                    f"Ativo: {p.ativo} | "
                    f"Adega ID: {p.adega_id}"
                )

            raise RuntimeError(
                "O perfil configurado não corresponde a um perfil ativo da adega."
            )

        print(f"Adega: {adega.nome}")
        print(f"Perfil: {perfil.nome}")

        nome = input("\nNome do usuário de teste: ").strip()
        email = input("E-mail de teste: ").strip().lower()

        senha = getpass.getpass("Senha de teste: ")
        confirmacao = getpass.getpass("Confirme a senha: ")

        if not nome or not email:
            raise ValueError(
                "Nome e e-mail são obrigatórios."
            )

        if senha != confirmacao:
            raise ValueError(
                "As senhas não coincidem."
            )

        if len(senha) < 10:
            raise ValueError(
                "A senha precisa ter pelo menos 10 caracteres."
            )

        if len(senha.encode("utf-8")) > 72:
            raise ValueError(
                "Senha excede o limite do bcrypt."
            )

        existente = db.execute(
            select(Usuario).where(
                Usuario.email == email
            )
        ).scalar_one_or_none()

        if existente is not None:
            raise RuntimeError(
                "E-mail já cadastrado."
            )

        usuario = Usuario(
            nome=nome,
            email=email,
            senha_hash=get_password_hash(senha),
            adega_id=ADEGA_ID,
            perfil_id=PERFIL_ID,
            is_platform_admin=False,
        )

        db.add(usuario)
        db.flush()

        print("\nUsuário preparado:")
        print(f"ID: {usuario.id}")
        print(f"Adega ID: {usuario.adega_id}")
        print(f"Perfil ID: {usuario.perfil_id}")
        print("Administrador global: NÃO")

    print("\nUsuário de teste criado com sucesso!")


if __name__ == "__main__":
    try:
        criar_usuario_teste()
    except Exception as erro:
        print(f"\nOperação cancelada: {erro}")
        raise SystemExit(1)
