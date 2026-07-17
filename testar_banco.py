from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import engine


def testar_conexao():
    try:
        with engine.connect() as conexao:
            versao = conexao.execute(
                text("SELECT version()")
            ).scalar()

            resultado = conexao.execute(
                text("""
                    SELECT
                        id,
                        nome,
                        email,
                        perfil_id,
                        adega_id
                    FROM usuarios
                    ORDER BY id
                """)
            )

            usuarios = resultado.mappings().all()

            print("\nConexão com o banco realizada com sucesso!")
            print(f"Banco: {versao}\n")

            if not usuarios:
                print("A tabela usuarios está vazia.")
                return

            print(f"Quantidade de usuários: {len(usuarios)}\n")

            for usuario in usuarios:
                print("-" * 50)
                print(f"ID:        {usuario['id']}")
                print(f"Nome:      {usuario['nome']}")
                print(f"E-mail:    {usuario['email']}")
                print(f"Perfil ID: {usuario['perfil_id']}")
                print(f"Adega ID:  {usuario['adega_id']}")

            print("-" * 50)

    except SQLAlchemyError as erro:
        print("\nNão foi possível acessar o banco.")
        print(f"Tipo do erro: {type(erro).__name__}")
        print(f"Detalhes: {erro}")

    except Exception as erro:
        print("\nOcorreu um erro inesperado.")
        print(f"Tipo do erro: {type(erro).__name__}")
        print(f"Detalhes: {erro}")


if __name__ == "__main__":
    testar_conexao()