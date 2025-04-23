from flask import Flask, render_template, redirect, url_for, session, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from flask_dance.contrib.google import make_google_blueprint, google
import os
import json
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
app.secret_key = "segredo123"

ADMIN_SENHA = "form123"

# Configurações do Google OAuth
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
if os.getenv("FLASK_ENV") == "development":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
os.environ["REDIRECT_URI"] = "https://quiz-unemat.onrender.com/login/google/authorized"

google_bp = make_google_blueprint(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    scope=["email", "profile"],
    redirect_to="quiz",
    authorized_url="https://quiz-unemat.onrender.com/login/google/authorized"
)
app.register_blueprint(google_bp, url_prefix="/login")

# 🧠 Armazenamento em memória (reseta quando reiniciar)
respostas_em_memoria = {}

@app.route("/")
def home():
    return redirect(url_for("index"))

@app.route("/index")
def index():
    return render_template("index.html")

@app.route("/quiz")
def quiz():
    if not google.authorized:
        return redirect(url_for("google.login"))

    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        return "Erro ao obter dados do usuário", 403

    email = resp.json()["email"]
    if not email.endswith("@unemat.br"):
        return "Acesso permitido somente para e-mails da UNEMAT.", 403

    session["email"] = email

    with open("data/perguntas.json", encoding="utf-8") as f:
        perguntas = json.load(f)

    return render_template("quiz.html", email=email, perguntas=perguntas)

@app.route("/api/responder/<int:pid>", methods=["POST"])
def responder(pid):
    dados = request.get_json()
    resposta = dados.get("resposta")
    pid_str = str(pid)

    if pid_str not in respostas_em_memoria:
        respostas_em_memoria[pid_str] = {}

    if resposta not in respostas_em_memoria[pid_str]:
        respostas_em_memoria[pid_str][resposta] = 0

    respostas_em_memoria[pid_str][resposta] += 1

    socketio.emit("nova_resposta", {
        "pergunta_id": pid,
        "resposta": resposta,
        "total": respostas_em_memoria[pid_str][resposta]
    }, broadcast=True)

    return jsonify({"status": "ok"})

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        senha = request.form.get("senha")
        if senha == ADMIN_SENHA:
            session["admin_autenticado"] = True
            return redirect(url_for("admin"))
        return render_template("login_admin.html", erro="Senha incorreta")

    if not session.get("admin_autenticado"):
        return render_template("login_admin.html")

    with open("data/perguntas.json", encoding="utf-8") as f:
        perguntas = json.load(f)

    respostas = respostas_em_memoria
    total_participantes = sum(
        sum(alternativas.values()) for alternativas in respostas.values()
    )

    return render_template("admin.html",
                           perguntas=perguntas,
                           respostas=respostas,
                           total_participantes=total_participantes)

@app.route("/logout-admin")
def logout_admin():
    session.pop("admin_autenticado", None)
    return redirect(url_for("admin"))

@app.route("/api/pergunta/<int:pid>")
def get_pergunta(pid):
    try:
        with open("data/perguntas.json", encoding="utf-8") as f:
            perguntas = json.load(f)

        if pid >= len(perguntas):
            return "Pergunta não encontrada", 404

        pergunta = perguntas[pid]
        return jsonify({
            "id": pergunta["id"],
            "pergunta": pergunta["pergunta"],
            "opcoes": list(pergunta["alternativas"].values())
        })
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route("/resetar-respostas", methods=["POST"])
def resetar_respostas():
    respostas_em_memoria.clear()
    return jsonify({"status": "respostas resetadas"})

@app.route("/resultado")
def resultado():
    email = session.get("email", "Desconhecido")

    with open("data/perguntas.json", encoding="utf-8") as f:
        perguntas = json.load(f)

    respostas = respostas_em_memoria

    return render_template("resultado.html", email=email, respostas=respostas, perguntas=perguntas)

@app.route("/static/perguntas.json")
def perguntas_estaticas():
    return send_from_directory("data", "perguntas.json")

@app.route("/api/respostas")
def api_respostas():
    return jsonify(respostas_em_memoria)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))  # Porta diferente
    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=os.environ.get("DEBUG", "False") == "True"
    )

