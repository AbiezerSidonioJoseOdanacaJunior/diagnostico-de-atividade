"""Importa somente as questões iniciais quando o banco de produção está vazio."""
import json
import os
import sqlite3

QUESTOES = json.loads('[{"habilidade": "interpretacao", "enunciado": "“A biblioteca da escola passou a abrir também durante o intervalo. Com isso, mais estudantes começaram a frequentar o espaço para ler e emprestar livros.”\\r\\n\\r\\nQual foi a consequência da mudança no horário da biblioteca?", "alternativa_a": "A biblioteca deixou de emprestar livros", "alternativa_b": "Mais estudantes passaram a frequentar a biblioteca", "alternativa_c": "Os estudantes deixaram de ler durante o intervalo.", "alternativa_d": "A biblioteca passou a funcionar somente durante as aulas.", "resposta_correta": "B", "dificuldade": "facil", "ativa": 1, "data_cadastro": "16/09/2026 09:44"}, {"habilidade": "raciocinio_logico", "enunciado": "Observe a sequência numérica:\\r\\n\\r\\n2, 4, 8, 16, ___\\r\\n\\r\\nQual é o próximo número?", "alternativa_a": "18", "alternativa_b": "24", "alternativa_c": "32", "alternativa_d": "36", "resposta_correta": "C", "dificuldade": "facil", "ativa": 1, "data_cadastro": "21/09/2026 13:03"}, {"habilidade": "resolucao_problemas", "enunciado": "Uma turma precisa organizar 36 livros igualmente em 6 caixas. Quantos livros devem ser colocados em cada caixa?", "alternativa_a": "5 livros", "alternativa_b": " 6 livros", "alternativa_c": "7 livros", "alternativa_d": "8 livros", "resposta_correta": "B", "dificuldade": "facil", "ativa": 1, "data_cadastro": "21/09/2026 23:19"}, {"habilidade": "matematica", "enunciado": "Um caderno custa R$ 40,00 e está com desconto de 25%. Qual será o preço do caderno após o desconto?", "alternativa_a": "R$ 10,00", "alternativa_b": "R$ 20,00", "alternativa_c": "R$ 30,00", "alternativa_d": "R$ 35,00", "resposta_correta": "C", "dificuldade": "facil", "ativa": 1, "data_cadastro": "22/09/2026 15:27"}, {"habilidade": "argumentacao", "enunciado": "Um estudante afirma: “Todos os alunos da escola preferem estudar pela manhã, porque três colegas da minha turma disseram que gostam desse horário.”\\r\\n\\r\\nQual é o principal problema dessa conclusão?", "alternativa_a": "A opinião de três colegas não é suficiente para representar todos os alunos da escola.", "alternativa_b": "Nenhum estudante gosta de estudar pela manhã.", "alternativa_c": "A preferência pelo horário de estudo nunca pode ser investigada.", "alternativa_d": "Todos os estudantes devem ter a mesma preferência de horário.", "resposta_correta": "A", "dificuldade": "facil", "ativa": 1, "data_cadastro": "22/09/2026 15:29"}, {"habilidade": "graficos_tabelas", "enunciado": "Uma escola registrou a quantidade de alunos presentes em quatro dias da semana:\\r\\n\\r\\nSegunda-feira: 120 alunos\\r\\nTerça-feira: 135 alunos\\r\\nQuarta-feira: 110 alunos\\r\\nQuinta-feira: 145 alunos\\r\\n\\r\\nDe acordo com os dados apresentados, em qual dia houve a maior quantidade de alunos presentes?", "alternativa_a": "Segunda-feira", "alternativa_b": "Terça-feira", "alternativa_c": "Quarta-feira", "alternativa_d": "Quinta-feira", "resposta_correta": "D", "dificuldade": "facil", "ativa": 1, "data_cadastro": "22/09/2026 15:32"}]')
CAMINHO_BANCO = os.environ.get("DATABASE_PATH", "banco.db")


def importar():
    with sqlite3.connect(CAMINHO_BANCO, timeout=30) as conexao:
        conexao.execute("BEGIN IMMEDIATE")
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS questoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                habilidade TEXT NOT NULL,
                enunciado TEXT NOT NULL,
                alternativa_a TEXT NOT NULL,
                alternativa_b TEXT NOT NULL,
                alternativa_c TEXT NOT NULL,
                alternativa_d TEXT NOT NULL,
                resposta_correta TEXT NOT NULL,
                dificuldade TEXT NOT NULL,
                ativa INTEGER NOT NULL DEFAULT 1,
                data_cadastro TEXT NOT NULL
            )
        """)
        total = conexao.execute("SELECT COUNT(*) FROM questoes").fetchone()[0]
        if total:
            print(f"Importação ignorada: banco já contém {total} questão(ões).", flush=True)
            return
        conexao.executemany("""
            INSERT INTO questoes (
                habilidade, enunciado, alternativa_a, alternativa_b,
                alternativa_c, alternativa_d, resposta_correta,
                dificuldade, ativa, data_cadastro
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [tuple(q[col] for col in (
            "habilidade", "enunciado", "alternativa_a", "alternativa_b",
            "alternativa_c", "alternativa_d", "resposta_correta",
            "dificuldade", "ativa", "data_cadastro"
        )) for q in QUESTOES])
        print(f"Importadas {len(QUESTOES)} questões em {CAMINHO_BANCO}.", flush=True)


if __name__ == "__main__":
    importar()
