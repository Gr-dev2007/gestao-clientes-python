from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime
import pywhatkit
from templates import TEMPLATE_VENCIMENTO, TEMPLATE_OFERTA, TEMPLATE_NATAL

app = Flask(__name__)
app.secret_key = "controtec_secret"

DB_PATH = "database.db"

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
        vencimento = datetime.strptime(vencimento_str, "%Y-%m-%d").date()
        if 0 <= (vencimento - hoje).days <= 7:
            mensagem = TEMPLATE_VENCIMENTO.format(nome=nome, produto=produto, data=vencimento)

    elif tipo == "oferta":
        mensagem = TEMPLATE_OFERTA.format(nome=nome, produto=produto)

    elif tipo == "natal" and hoje.month == 12 and hoje.day == 25:
        mensagem = TEMPLATE_NATAL.format(nome=nome)

    return mensagem

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
                erros.append(c[1])
    flash(f"{enviados} mensagens enviadas.", "success")
    if erros:
        flash(f"Falha ao enviar para: {', '.join(erros)}", "error")
    return redirect(url_for("index"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
