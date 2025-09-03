# launcher.py
import os
import sys
import threading
import time
import webbrowser
import urllib.request

# Ajusta working directory para a pasta do executável (quando empacotado)
def get_workdir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.dirname(__file__))

os.chdir(get_workdir())

# Importar app (ele contém init_db e a instância Flask)
from app import app, init_db

# Garantir DB criado na pasta correta (lado do exe)
init_db()

def run_server():
    # importante: use_reloader=False para não criar processo filho
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)

# start server em thread
server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

# aguardar até o servidor responder
url = "http://127.0.0.1:5000/"
for i in range(60):  # até ~30s
    try:
        urllib.request.urlopen(url)
        break
    except Exception:
        time.sleep(0.5)

# abrir navegador padrão
webbrowser.open(url)

# manter o processo vivo enquanto o servidor roda
server_thread.join()
