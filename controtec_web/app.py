# app.py (versão adaptada para empacotamento)
import os
import sys
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime
import pywhatkit
from templates import TEMPLATE_VENCIMENTO, TEMPLATE_OFERTA, TEMPLATE_NATAL

# ----- Helpers para empacotamento -----
def get_base_path():
    """
    Retorna a pasta base correta:
    - quando empacotado com PyInstaller (frozen): sys._MEIPASS contém os recursos embutidos
    - quando executado normal: pasta do arquivo
    """
    if getattr(sys, "frozen", False):
        # PyInstaller extrai recursos em _MEIPASS
        return sys._MEIPASS
    return os.path.abspath(os.path.dirname(__file__))

# Diretório onde o Flask vai procurar templates está em get_base_path()/templates
BASE_RESOURCE_PATH = get_base_path()
TEMPLATES_FOLDER = os.path.join(BASE_RESOURCE_PATH, "templates")

# Diretório onde o banco deve ficar (persistente):
# - empacotado: colocaremos o DB ao lado do executável (diretório do exe)
# - desenvolvimento: ficará na pasta do projeto
def get_data_folder():
    if getattr(sys, "frozen", False):
        # diretório onde o executável está sendo executado -> persistência do DB
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.dirname(__file__))

DATA_FOLDER = get_data_folder()
DB_PATH = os.path.join(DATA_FOLDER, "database.db")

# Criar app apontando para a pasta de templates correta
app = Flask(__name__, template_folder=TEMPLATES_FOLDER)
app.secret_key = "controtec_secret"

# ---------- Banco ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT NOT NULL UNIQUE,
            produto TEXT,
            vencimento TEXT,
            tipo TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_clientes():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM clientes ORDER BY nome")
    clientes = c.fetchall()
    conn.close()
    return clientes

def get_cliente_by_id(cliente_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,))
    cliente = c.fetchone()
    conn.close()
    return cliente

def add_cliente_db(nome, telefone, produto, vencimento, tipo):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO clientes (nome, telefone, produto, vencimento, tipo) VALUES (?, ?, ?, ?, ?)",
                  (nome, telefone, produto, vencimento, tipo))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def update_cliente_db(cliente_id, nome, telefone, produto, vencimento, tipo):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("""
            UPDATE clientes
            SET nome = ?, telefone = ?, produto = ?, vencimento = ?, tipo = ?
            WHERE id = ?
        """, (nome, telefone, produto, vencimento, tipo, cliente_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # telefone duplicado
        return False
    finally:
        conn.close()

def delete_cliente_db(cliente_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
    conn.commit()
    conn.close()

# ---------- Mensagens ----------
def enviar_mensagem(numero, mensagem):
    try:
        now = datetime.now()
        envio_hora = now.hour
        envio_minuto = now.minute + 1
        if envio_minuto >= 60:
            envio_minuto = 0
            envio_hora = (envio_hora + 1) % 24
        pywhatkit.sendwhatmsg(numero, mensagem, envio_hora, envio_minuto)
        return True
    except Exception as e:
        print(f"Erro ao enviar para {numero}: {e}")
        return False

def montar_mensagem(cliente):
    hoje = datetime.now().date()
    nome = cliente[1]
    numero = cliente[2]
    produto = cliente[3]
    vencimento_str = cliente[4]
    tipo = cliente[5]

    mensagem = ""

    if tipo == "vencimento" and vencimento_str:
        try:
            vencimento = datetime.strptime(vencimento_str, "%Y-%m-%d").date()
            if 0 <= (vencimento - hoje).days <= 7:
                mensagem = TEMPLATE_VENCIMENTO.format(nome=nome, produto=produto, data=vencimento)
        except Exception:
            pass  # data inválida, ignora

    elif tipo == "oferta":
        mensagem = TEMPLATE_OFERTA.format(nome=nome, produto=produto)

    elif tipo == "natal" and hoje.month == 12 and hoje.day == 25:
        mensagem = TEMPLATE_NATAL.format(nome=nome)

    return mensagem

# ---------- Rotas ----------
@app.route("/")
def index():
    clientes = get_clientes()
    return render_template("index.html", clientes=clientes)

@app.route("/add", methods=["GET", "POST"])
def add_cliente():
    if request.method == "POST":
        nome = request.form.get("nome")
        telefone = request.form.get("telefone")
        produto = request.form.get("produto")
        vencimento = request.form.get("vencimento")
        tipo = request.form.get("tipo")

        if not nome or not telefone:
            flash("Nome e telefone são obrigatórios!", "error")
            return redirect(url_for("add_cliente"))

        sucesso = add_cliente_db(nome, telefone, produto, vencimento, tipo)
        if sucesso:
            flash("Cliente adicionado com sucesso!", "success")
            return redirect(url_for("index"))
        else:
            flash("Telefone já cadastrado!", "error")
            return redirect(url_for("add_cliente"))

    return render_template("add_cliente.html")

@app.route("/editar/<int:cliente_id>", methods=["GET", "POST"])
def editar_cliente(cliente_id):
    cliente = get_cliente_by_id(cliente_id)
    if not cliente:
        flash("Cliente não encontrado.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        nome = request.form.get("nome")
        telefone = request.form.get("telefone")
        produto = request.form.get("produto")
        vencimento = request.form.get("vencimento")
        tipo = request.form.get("tipo")

        if not nome or not telefone:
            flash("Nome e telefone são obrigatórios!", "error")
            return redirect(url_for("editar_cliente", cliente_id=cliente_id))

        sucesso = update_cliente_db(cliente_id, nome, telefone, produto, vencimento, tipo)
        if sucesso:
            flash("Cliente atualizado com sucesso!", "success")
        else:
            flash("Falha ao atualizar (telefone pode já estar cadastrado).", "error")
        return redirect(url_for("index"))

    return render_template("edit_cliente.html", cliente=cliente)

@app.route("/excluir/<int:cliente_id>", methods=["POST"])
def excluir_cliente(cliente_id):
    cliente = get_cliente_by_id(cliente_id)
    if not cliente:
        flash("Cliente não encontrado.", "error")
    else:
        delete_cliente_db(cliente_id)
        flash("Cliente excluído com sucesso.", "success")
    return redirect(url_for("index"))

@app.route("/enviar")
def enviar():
    clientes = get_clientes()
    erros = []
    enviados = 0
    for c in clientes:
        mensagem = montar_mensagem(c)
        if mensagem:
            if enviar_mensagem(c[2], mensagem):
                enviados += 1
            else:
                erros.append(c[1] or str(c[0]))
    flash(f"{enviados} mensagens agendadas.", "success")
    if erros:
        flash(f"Falha ao agendar para: {', '.join(erros)}", "error")
    return redirect(url_for("index"))

# ---------- Inicialização ----------
if __name__ == "__main__":
    # cria DB (ou garante que exista) no local persistente definido por DB_PATH
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=False)
