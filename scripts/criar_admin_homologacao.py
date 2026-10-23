
import getpass
from sqlalchemy import select, text

from app.database import SessionLocal
from app.models import Adega, Perfil, Usuario
from app.security import get_password_hash


NOME_ADEGA_ADMIN = "IMBEBI Tec - Administração"
BANCO_ESPERADO = "adegas_teste"


def criar_administrador():
    print("\n=== ADMINISTRADOR IMBEBI ===")
    print("Ambiente: HOMOLOGAÇÃO\n")

    email = input("E-mail do administrador: ").strip().lower()
    nome = input("Nome do administrador: ").strip()

    senha = getpass.getpass("Digite uma senha forte: ")
    confirmacao = getpass.getpass("Confirme a senha: ")

    if not email or not nome:
        raise ValueError("Nome e e-mail são obrigatórios.")

    if senha != confirmacao:
        raise ValueError("As senhas não coincidem.")

    if len(senha) < 10:
        raise ValueError("Utilize pelo menos 10 caracteres.")

    if len(senha.encode("utf-8")) > 72:
        raise ValueError("A senha excede o limite do bcrypt.")

    senha_hash = get_password_hash(senha)

    with SessionLocal.begin() as db:
        banco_atual = db.execute(
            text("SELECT current_database()")
        ).scalar_one()

        print(f"\nBanco conectado: {banco_atual}")

        if banco_atual != BANCO_ESPERADO:
            raise RuntimeError(
                "Banco incorreto! Operação cancelada."
            )

        admin_existente = db.execute(
            select(Usuario).where(
                Usuario.is_platform_admin.is_(True)
            )
        ).first()

        if admin_existente:
            raise RuntimeError(
                "Já existe administrador global. "
                "Operação cancelada."
            )

        usuario_existente = db.execute(
            select(Usuario).where(Usuario.email == email)
        ).first()

        if usuario_existente:
            raise RuntimeError(
                "E-mail já cadastrado. Operação cancelada."
            )

        adega_existente = db.execute(
            select(Adega).where(
                Adega.nome == NOME_ADEGA_ADMIN
            )
        ).first()

        if adega_existente:
            raise RuntimeError(
                "Adega administrativa já existe. "
                "Operação cancelada."
            )

        adega = Adega(
            nome=NOME_ADEGA_ADMIN,
            email=email,
            plano="pago",
            status_assinatura="ativo",
            notificacao_ativa=False,
        )
        db.add(adega)
        db.flush()

        perfil = Perfil(
            adega_id=adega.id,
            nome="Administrador IMBEBI",
            descricao="Administração global da plataforma",
            eh_admin=True,
            pode_gerenciar_usuarios=True,
            pode_gerenciar_estoque=False,
            pode_gerenciar_clientes=False,
            ativo=True,
        )
        db.add(perfil)
        db.flush()

        usuario = Usuario(
            adega_id=adega.id,
            perfil_id=perfil.id,
            nome=nome,
            email=email,
            senha_hash=senha_hash,
            is_platform_admin=True,
        )
        db.add(usuario)
        db.flush()

        print("\nRegistros preparados:")
        print(f"Adega administrativa: {adega.id}")
        print(f"Perfil: {perfil.id}")
        print(f"Usuário: {usuario.id}")

    print("\nAdministrador criado com sucesso!")


if __name__ == "__main__":
    try:
        criar_administrador()
    except Exception as erro:
        print(f"\nOperação cancelada: {erro}")
        raise SystemExit(1)
