from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime
from functools import wraps
from werkzeug.security import check_password_hash

app = Flask(__name__)

import os
CAMINHO_BANCO = os.environ.get("DATABASE_PATH", "banco.db")

app.secret_key = os.environ.get("FLASK_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError(
        "FLASK_SECRET_KEY não configurada. "
        "Defina essa variável de ambiente antes de iniciar o sistema."
    )


# =========================================================
# BANCO DE DADOS
# =========================================================

def conectar_banco():
    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row

    # Ativa o suporte às chaves estrangeiras do SQLite
    conexao.execute("PRAGMA foreign_keys = ON")

    return conexao


def criar_tabelas():

    conexao = conectar_banco()

    # -------------------------
    # ESTUDANTES
    # -------------------------

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS estudantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            idade INTEGER NOT NULL,
            serie TEXT NOT NULL,
            curso_tecnico TEXT NOT NULL,
            data_realizacao TEXT NOT NULL
        )
    """)

    # -------------------------
    # QUESTÕES
    # -------------------------

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

    # -------------------------
    # RESULTADOS
    # -------------------------

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS resultados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            estudante_id INTEGER NOT NULL,

            interpretacao REAL DEFAULT 0,
            raciocinio_logico REAL DEFAULT 0,
            resolucao_problemas REAL DEFAULT 0,
            graficos_tabelas REAL DEFAULT 0,
            matematica REAL DEFAULT 0,
            argumentacao REAL DEFAULT 0,

            media_geral REAL DEFAULT 0,

            FOREIGN KEY (estudante_id)
            REFERENCES estudantes (id)
        )
    """)

    # -------------------------
    # RESPOSTAS
    # -------------------------

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS respostas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            estudante_id INTEGER NOT NULL,

            questao_id INTEGER NOT NULL,

            resposta_marcada TEXT,

            correta INTEGER NOT NULL,

            FOREIGN KEY (estudante_id)
            REFERENCES estudantes (id),

            FOREIGN KEY (questao_id)
            REFERENCES questoes (id)
        )
    """)

    conexao.commit()
    conexao.close()


criar_tabelas()

# =========================================================
# AUTENTICAÇÃO DO ADMINISTRADOR
# =========================================================

ADMIN_USUARIO = os.environ.get("ADMIN_USUARIO")
ADMIN_SENHA_HASH = os.environ.get("ADMIN_SENHA_HASH")


def administrador_autenticado():
    return session.get("admin_autenticado") is True


def login_obrigatorio(funcao):
    @wraps(funcao)
    def verificar_acesso(*args, **kwargs):

        if not administrador_autenticado():
            return redirect(url_for("login_admin"))

        return funcao(*args, **kwargs)

    return verificar_acesso


@app.route("/admin/login", methods=["GET", "POST"])
def login_admin():

    if administrador_autenticado():
        return redirect(url_for("admin"))

    if request.method == "POST":

        usuario = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "")

        if not ADMIN_USUARIO or not ADMIN_SENHA_HASH:
            flash(
                "O acesso administrativo ainda não foi configurado.",
                "erro"
            )
            return render_template("login_admin.html"), 503

        usuario_correto = usuario == ADMIN_USUARIO

        senha_correta = check_password_hash(
            ADMIN_SENHA_HASH,
            senha
        )

        if usuario_correto and senha_correta:

            # Evita manter dados de um estudante na sessão
            # utilizada para o acesso administrativo.
            session.clear()

            session["admin_autenticado"] = True

            return redirect(url_for("admin"))

        flash("Usuário ou senha incorretos.", "erro")

    return render_template("login_admin.html")


@app.route("/admin/sair", methods=["POST"])
@login_obrigatorio
def sair_admin():

    session.clear()

    return redirect(url_for("login_admin"))


# =========================================================
# PÁGINA INICIAL
# =========================================================

@app.route("/")
def inicio():
    return render_template("index.html")


# =========================================================
# IDENTIFICAÇÃO
# =========================================================

@app.route("/identificacao", methods=["GET", "POST"])
def identificacao():

    if request.method == "POST":

        nome = request.form.get("nome")
        serie = request.form.get("serie")
        idade = request.form.get("idade")
        curso_tecnico = request.form.get("curso_tecnico")

        conexao = conectar_banco()

        cursor = conexao.execute("""
            INSERT INTO estudantes
            (
                nome,
                idade,
                serie,
                curso_tecnico,
                data_realizacao
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            nome,
            idade,
            serie,
            curso_tecnico,
            datetime.now().strftime("%d/%m/%Y %H:%M")
        ))

        estudante_id = cursor.lastrowid
        session["estudante_id"] = estudante_id

        conexao.commit()
        conexao.close()

        return redirect(url_for("instrucoes"))

    return render_template("identificacao.html")


# =========================================================
# INSTRUÇÕES
# =========================================================

# =========================================================
# INSTRUÇÕES
# =========================================================

@app.route("/instrucoes")
def instrucoes():

    if "estudante_id" not in session:
        return redirect(url_for("identificacao"))

    return render_template("instrucoes.html")


# =========================================================
# DIAGNÓSTICO
# =========================================================

@app.route("/diagnostico", methods=["GET", "POST"])
def diagnostico():

    estudante_id = session.get("estudante_id")

    if estudante_id is None:
        return redirect(url_for("identificacao"))

    conexao = conectar_banco()

    # Verifica se o estudante existe.
    estudante = conexao.execute("""
        SELECT id
        FROM estudantes
        WHERE id = ?
    """, (estudante_id,)).fetchone()

    if estudante is None:
        conexao.close()
        session.pop("estudante_id", None)
        return redirect(url_for("identificacao"))

    # Busca as questões ativas que ainda não foram respondidas.
    questoes_pendentes = conexao.execute("""
        SELECT
            q.id,
            q.habilidade,
            q.enunciado,
            q.alternativa_a,
            q.alternativa_b,
            q.alternativa_c,
            q.alternativa_d
        FROM questoes AS q
        WHERE q.ativa = 1
        AND NOT EXISTS (
            SELECT 1
            FROM respostas AS r
            WHERE r.questao_id = q.id
            AND r.estudante_id = ?
        )
        ORDER BY q.id ASC
    """, (estudante_id,)).fetchall()

    # Total de questões ativas.
    total_questoes = conexao.execute("""
        SELECT COUNT(*) AS total
        FROM questoes
        WHERE ativa = 1
    """).fetchone()["total"]

    # Total de respostas já registradas para questões ativas.
    respondidas = conexao.execute("""
        SELECT COUNT(DISTINCT r.questao_id) AS total
        FROM respostas AS r
        INNER JOIN questoes AS q
            ON q.id = r.questao_id
        WHERE r.estudante_id = ?
        AND q.ativa = 1
    """, (estudante_id,)).fetchone()["total"]

    # -----------------------------------------------------
    # RECEBER RESPOSTA
    # -----------------------------------------------------

    if request.method == "POST":

        questao_id = request.form.get(
            "questao_id",
            type=int
        )

        resposta_marcada = request.form.get(
            "resposta_marcada",
            ""
        ).strip().upper()

        if resposta_marcada not in ("A", "B", "C", "D"):
            conexao.close()
            return "Selecione uma alternativa válida.", 400

        # A resposta só pode ser enviada para uma questão
        # ativa e ainda não respondida pelo estudante.
        questao = conexao.execute("""
            SELECT
                id,
                resposta_correta
            FROM questoes
            WHERE id = ?
            AND ativa = 1
            AND NOT EXISTS (
                SELECT 1
                FROM respostas
                WHERE estudante_id = ?
                AND questao_id = ?
            )
        """, (
            questao_id,
            estudante_id,
            questao_id
        )).fetchone()

        if questao is None:
            conexao.close()
            return redirect(url_for("diagnostico"))

        correta = int(
            resposta_marcada == questao["resposta_correta"]
        )

        conexao.execute("""
            INSERT INTO respostas
            (
                estudante_id,
                questao_id,
                resposta_marcada,
                correta
            )
            VALUES (?, ?, ?, ?)
        """, (
            estudante_id,
            questao_id,
            resposta_marcada,
            correta
        ))

        conexao.commit()
        conexao.close()

        return redirect(url_for("diagnostico"))

    # -----------------------------------------------------
    # EXIBIR PRÓXIMA QUESTÃO
    # -----------------------------------------------------

    if total_questoes == 0:

        conexao.close()

        return render_template(
            "diagnostico.html",
            sem_questoes=True
        )

    if not questoes_pendentes:

        conexao.close()

        return redirect(url_for("resultado"))

    questao = questoes_pendentes[0]

    numero_questao = respondidas + 1

    progresso = round(
        (respondidas / total_questoes) * 100
    )

    conexao.close()

    return render_template(
        "diagnostico.html",
        questao=questao,
        numero_questao=numero_questao,
        total_questoes=total_questoes,
        progresso=progresso,
        sem_questoes=False
    )


# =========================================================
# RESULTADO INDIVIDUAL DO DIAGNÓSTICO
# =========================================================

@app.route("/resultado")
def resultado():

    estudante_id = session.get("estudante_id")

    if estudante_id is None:
        return redirect(url_for("identificacao"))

    conexao = conectar_banco()

    estudante = conexao.execute("""
        SELECT *
        FROM estudantes
        WHERE id = ?
    """, (estudante_id,)).fetchone()

    if estudante is None:
        conexao.close()
        session.pop("estudante_id", None)
        return redirect(url_for("identificacao"))

    # Verifica se ainda existem questões ativas não respondidas.
    pendentes = conexao.execute("""
        SELECT COUNT(*) AS total
        FROM questoes AS q
        WHERE q.ativa = 1
        AND NOT EXISTS (
            SELECT 1
            FROM respostas AS r
            WHERE r.questao_id = q.id
            AND r.estudante_id = ?
        )
    """, (estudante_id,)).fetchone()["total"]

    total_respostas = conexao.execute("""
        SELECT COUNT(*) AS total
        FROM respostas
        WHERE estudante_id = ?
    """, (estudante_id,)).fetchone()["total"]

    # Não permite visualizar um resultado antes de concluir.
    if pendentes > 0 or total_respostas == 0:
        conexao.close()
        return redirect(url_for("diagnostico"))

    habilidades = {
        "interpretacao": "Interpretação e compreensão textual",
        "raciocinio_logico": "Raciocínio lógico",
        "resolucao_problemas": "Resolução de problemas",
        "graficos_tabelas": "Leitura de gráficos e tabelas",
        "matematica": "Conhecimentos matemáticos básicos",
        "argumentacao": "Argumentação e análise de informações"
    }

    # Calcula os acertos por habilidade.
    dados = conexao.execute("""
        SELECT
            q.habilidade,
            COUNT(*) AS total,
            SUM(r.correta) AS acertos
        FROM respostas AS r
        INNER JOIN questoes AS q
            ON q.id = r.questao_id
        WHERE r.estudante_id = ?
        GROUP BY q.habilidade
    """, (estudante_id,)).fetchall()

    resultados_habilidades = []

    # Inicia todas as habilidades com zero.
    # Uma habilidade sem questões respondidas ficará sem nota.
    percentuais = {
        habilidade: 0.0
        for habilidade in habilidades
    }

    total_acertos = 0
    total_questoes = 0

    dados_por_habilidade = {
        linha["habilidade"]: linha
        for linha in dados
    }

    for codigo, nome in habilidades.items():

        linha = dados_por_habilidade.get(codigo)

        if linha is None:
            total = 0
            acertos = 0
            percentual = None

        else:
            total = linha["total"]
            acertos = linha["acertos"] or 0

            percentual = round(
                (acertos / total) * 100,
                1
            ) if total > 0 else None

        if percentual is not None:
            percentuais[codigo] = percentual

        total_acertos += acertos
        total_questoes += total

        resultados_habilidades.append({
            "codigo": codigo,
            "nome": nome,
            "total": total,
            "acertos": acertos,
            "percentual": percentual
        })

    media_geral = round(
        (total_acertos / total_questoes) * 100,
        1
    ) if total_questoes > 0 else 0.0

    # -----------------------------------------------------
    # SALVAR O RESULTADO NO BANCO
    # -----------------------------------------------------

    resultado_existente = conexao.execute("""
        SELECT id
        FROM resultados
        WHERE estudante_id = ?
    """, (estudante_id,)).fetchone()

    valores = (
        percentuais["interpretacao"],
        percentuais["raciocinio_logico"],
        percentuais["resolucao_problemas"],
        percentuais["graficos_tabelas"],
        percentuais["matematica"],
        percentuais["argumentacao"],
        media_geral
    )

    if resultado_existente:

        conexao.execute("""
            UPDATE resultados
            SET
                interpretacao = ?,
                raciocinio_logico = ?,
                resolucao_problemas = ?,
                graficos_tabelas = ?,
                matematica = ?,
                argumentacao = ?,
                media_geral = ?
            WHERE estudante_id = ?
        """, valores + (estudante_id,))

    else:

        conexao.execute("""
            INSERT INTO resultados (
                interpretacao,
                raciocinio_logico,
                resolucao_problemas,
                graficos_tabelas,
                matematica,
                argumentacao,
                media_geral,
                estudante_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, valores + (estudante_id,))

    conexao.commit()
    conexao.close()

    return render_template(
        "resultado.html",
        estudante=estudante,
        resultados_habilidades=resultados_habilidades,
        media_geral=media_geral,
        total_acertos=total_acertos,
        total_questoes=total_questoes
    )



# =========================================================
# PAINEL ADMINISTRATIVO
# =========================================================

@app.route("/admin")
@login_obrigatorio
def admin():

    conexao = conectar_banco()

    estudantes = conexao.execute("""
        SELECT
            e.id,
            e.nome,
            e.idade,
            e.serie,
            e.curso_tecnico,
            e.data_realizacao,

            r.id AS resultado_id,
            r.media_geral,

            (
                SELECT COUNT(*)
                FROM respostas AS resp
                WHERE resp.estudante_id = e.id
            ) AS total_respostas

        FROM estudantes AS e

        LEFT JOIN resultados AS r
            ON r.id = (
                SELECT MAX(r2.id)
                FROM resultados AS r2
                WHERE r2.estudante_id = e.id
            )

        ORDER BY e.id DESC
    """).fetchall()

    total_estudantes = conexao.execute("""
        SELECT COUNT(*) AS total
        FROM estudantes
    """).fetchone()["total"]

    total_concluidos = conexao.execute("""
        SELECT COUNT(DISTINCT estudante_id) AS total
        FROM resultados
    """).fetchone()["total"]

    total_questoes = conexao.execute("""
        SELECT COUNT(*) AS total
        FROM questoes
    """).fetchone()["total"]

    questoes_ativas = conexao.execute("""
        SELECT COUNT(*) AS total
        FROM questoes
        WHERE ativa = 1
    """).fetchone()["total"]

    # Considera o registro mais recente de resultado de cada estudante.
    medias = conexao.execute("""
        SELECT
            ROUND(AVG(r.media_geral), 1) AS media_geral,

            ROUND(AVG(r.interpretacao), 1) AS interpretacao,
            ROUND(AVG(r.raciocinio_logico), 1) AS raciocinio_logico,
            ROUND(AVG(r.resolucao_problemas), 1) AS resolucao_problemas,
            ROUND(AVG(r.graficos_tabelas), 1) AS graficos_tabelas,
            ROUND(AVG(r.matematica), 1) AS matematica,
            ROUND(AVG(r.argumentacao), 1) AS argumentacao

        FROM resultados AS r

        WHERE r.id = (
            SELECT MAX(r2.id)
            FROM resultados AS r2
            WHERE r2.estudante_id = r.estudante_id
        )
    """).fetchone()

    habilidades = [
        {
            "nome": "Interpretação e compreensão textual",
            "media": medias["interpretacao"]
        },
        {
            "nome": "Raciocínio lógico",
            "media": medias["raciocinio_logico"]
        },
        {
            "nome": "Resolução de problemas",
            "media": medias["resolucao_problemas"]
        },
        {
            "nome": "Leitura de gráficos e tabelas",
            "media": medias["graficos_tabelas"]
        },
        {
            "nome": "Conhecimentos matemáticos básicos",
            "media": medias["matematica"]
        },
        {
            "nome": "Argumentação e análise de informações",
            "media": medias["argumentacao"]
        }
    ]

    conexao.close()

    return render_template(
        "admin.html",
        estudantes=estudantes,
        total_estudantes=total_estudantes,
        total_concluidos=total_concluidos,
        total_questoes=total_questoes,
        questoes_ativas=questoes_ativas,
        media_geral=medias["media_geral"],
        habilidades=habilidades
    )

# =========================================================
# RESULTADO INDIVIDUAL NO PAINEL ADMINISTRATIVO
# =========================================================

@app.route("/admin/resultado/<int:estudante_id>")
@login_obrigatorio
def admin_resultado(estudante_id):
    conexao = conectar_banco()

    estudante = conexao.execute("""
        SELECT *
        FROM estudantes
        WHERE id = ?
    """, (estudante_id,)).fetchone()

    if estudante is None:
        conexao.close()
        return "Estudante não encontrado.", 404

    resultado = conexao.execute("""
        SELECT *
        FROM resultados
        WHERE estudante_id = ?
        ORDER BY id DESC
        LIMIT 1
    """, (estudante_id,)).fetchone()

    if resultado is None:
        conexao.close()
        return redirect(url_for("admin"))

    dados = conexao.execute("""
        SELECT
            q.habilidade,
            COUNT(*) AS total,
            SUM(r.correta) AS acertos

        FROM respostas AS r

        INNER JOIN questoes AS q
            ON q.id = r.questao_id

        WHERE r.estudante_id = ?

        GROUP BY q.habilidade
    """, (estudante_id,)).fetchall()

    nomes_habilidades = {
        "interpretacao": "Interpretação e compreensão textual",
        "raciocinio_logico": "Raciocínio lógico",
        "resolucao_problemas": "Resolução de problemas",
        "graficos_tabelas": "Leitura de gráficos e tabelas",
        "matematica": "Conhecimentos matemáticos básicos",
        "argumentacao": "Argumentação e análise de informações"
    }

    dados_por_habilidade = {
        linha["habilidade"]: linha
        for linha in dados
    }

    resultados_habilidades = []

    total_acertos = 0
    total_questoes = 0

    for codigo, nome in nomes_habilidades.items():

        linha = dados_por_habilidade.get(codigo)

        if linha is None:
            acertos = 0
            total = 0
            percentual = None

        else:
            acertos = linha["acertos"] or 0
            total = linha["total"]

            percentual = round(
                (acertos / total) * 100,
                1
            ) if total > 0 else None

        total_acertos += acertos
        total_questoes += total

        resultados_habilidades.append({
            "nome": nome,
            "acertos": acertos,
            "total": total,
            "percentual": percentual
        })

    conexao.close()

    return render_template(
        "admin_resultado.html",
        estudante=estudante,
        resultado=resultado,
        resultados_habilidades=resultados_habilidades,
        total_acertos=total_acertos,
        total_questoes=total_questoes
    )

# =========================================================
# LISTAR QUESTÕES
# =========================================================

@app.route("/admin/questoes")
@login_obrigatorio
def listar_questoes():

    conexao = conectar_banco()

    questoes = conexao.execute("""
        SELECT *
        FROM questoes
        ORDER BY id DESC
    """).fetchall()

    conexao.close()

    return render_template(
        "questoes.html",
        questoes=questoes
    )


# =========================================================
# CADASTRAR QUESTÃO
# =========================================================

@app.route("/admin/questoes/nova", methods=["GET", "POST"])
@login_obrigatorio
def nova_questao():

    if request.method == "POST":

        habilidade = request.form.get("habilidade")
        enunciado = request.form.get("enunciado")

        alternativa_a = request.form.get("alternativa_a")
        alternativa_b = request.form.get("alternativa_b")
        alternativa_c = request.form.get("alternativa_c")
        alternativa_d = request.form.get("alternativa_d")

        resposta_correta = request.form.get("resposta_correta")
        dificuldade = request.form.get("dificuldade")

        conexao = conectar_banco()

        conexao.execute("""
            INSERT INTO questoes
            (
                habilidade,
                enunciado,
                alternativa_a,
                alternativa_b,
                alternativa_c,
                alternativa_d,
                resposta_correta,
                dificuldade,
                ativa,
                data_cadastro
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            habilidade,
            enunciado,
            alternativa_a,
            alternativa_b,
            alternativa_c,
            alternativa_d,
            resposta_correta,
            dificuldade,
            1,
            datetime.now().strftime("%d/%m/%Y %H:%M")
        ))

        conexao.commit()
        conexao.close()

        return redirect(
            url_for("listar_questoes")
        )

    return render_template("nova_questao.html")


# =========================================================
# EDITAR QUESTÃO
# =========================================================

@app.route(
    "/admin/questoes/editar/<int:id>",
    
    methods=["GET", "POST"]
)
@login_obrigatorio
def editar_questao(id):

    conexao = conectar_banco()

    questao = conexao.execute("""
        SELECT *
        FROM questoes
        WHERE id = ?
    """, (id,)).fetchone()

    if questao is None:

        conexao.close()

        return "Questão não encontrada.", 404

    if request.method == "POST":

        habilidade = request.form.get("habilidade")
        enunciado = request.form.get("enunciado")

        alternativa_a = request.form.get("alternativa_a")
        alternativa_b = request.form.get("alternativa_b")
        alternativa_c = request.form.get("alternativa_c")
        alternativa_d = request.form.get("alternativa_d")

        resposta_correta = request.form.get("resposta_correta")
        dificuldade = request.form.get("dificuldade")

        conexao.execute("""
            UPDATE questoes

            SET habilidade = ?,
                enunciado = ?,
                alternativa_a = ?,
                alternativa_b = ?,
                alternativa_c = ?,
                alternativa_d = ?,
                resposta_correta = ?,
                dificuldade = ?

            WHERE id = ?
        """, (
            habilidade,
            enunciado,
            alternativa_a,
            alternativa_b,
            alternativa_c,
            alternativa_d,
            resposta_correta,
            dificuldade,
            id
        ))

        conexao.commit()
        conexao.close()

        return redirect(
            url_for("listar_questoes")
        )

    conexao.close()

    return render_template(
        "editar_questao.html",
        questao=questao
    )


# =========================================================
# ATIVAR / DESATIVAR QUESTÃO
# =========================================================

@app.route(
    "/admin/questoes/status/<int:id>",
    methods=["POST"]
)
@login_obrigatorio
def alterar_status_questao(id):

    conexao = conectar_banco()

    questao = conexao.execute("""
        SELECT ativa
        FROM questoes
        WHERE id = ?
    """, (id,)).fetchone()

    if questao is None:

        conexao.close()

        return "Questão não encontrada.", 404

    novo_status = 0 if questao["ativa"] == 1 else 1

    conexao.execute("""
        UPDATE questoes
        SET ativa = ?
        WHERE id = ?
    """, (
        novo_status,
        id
    ))

    conexao.commit()
    conexao.close()

    return redirect(
        url_for("listar_questoes")
    )


# =========================================================
# EXECUTAR
# =========================================================
if __name__ == "__main__":
    app.run(debug=False)