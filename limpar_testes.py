import sqlite3

BANCO = "banco.db"

confirmacao = input(
    "ATENÇÃO: apagar todos os estudantes, respostas e resultados de teste? "
    "Digite LIMPAR para confirmar: "
)

if confirmacao != "LIMPAR":
    print("Operação cancelada. Nenhum dado foi apagado.")

else:
    conexao = sqlite3.connect(BANCO)

    try:
        conexao.execute("PRAGMA foreign_keys = ON")

        with conexao:
            # Apaga primeiro os dados vinculados aos estudantes.
            conexao.execute("DELETE FROM respostas")
            conexao.execute("DELETE FROM resultados")

            # Apaga os cadastros utilizados nos testes.
            conexao.execute("DELETE FROM estudantes")

        print("Limpeza concluída!")
        print("Estudantes, respostas e resultados foram apagados.")
        print("As questões cadastradas foram preservadas.")

    except sqlite3.Error as erro:
        print("Erro ao limpar os testes:", erro)

    finally:
        conexao.close()