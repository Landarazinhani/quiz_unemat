from flask import Flask, render_template, redirect, url_for, session, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from flask_dance.contrib.google import make_google_blueprint, google
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Config Google OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

app = Flask(__name__)
app.secret_key = "segredo123"
socketio = SocketIO(app, cors_allowed_origins="*")

ADMIN_SENHA = "form123"

# Ambiente de desenvolvimento permite HTTP
if os.getenv("FLASK_ENV") == "development":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

# Blueprint do Google com redirect_uri correto
google_bp = make_google_blueprint(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    scope=["email", "profile"],
    redirect_to="quiz"
)

app.register_blueprint(google_bp, url_prefix="/login")

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

    with open("data/respostas.json", encoding="utf-8") as f:
        respostas = json.load(f)

    total_participantes = sum(
        sum(alternativas.values()) for alternativas in respostas.values()
    )

    return render_template("admin.html", perguntas=perguntas, respostas=respostas, total_participantes=total_participantes)

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

@app.route("/api/responder/<int:pid>", methods=["POST"])
def responder(pid):
    dados = request.get_json()
    resposta = dados.get("resposta")

    with open("data/respostas.json", "r", encoding="utf-8") as f:
        respostas = json.load(f)

    pid_str = str(pid)
    if pid_str not in respostas:
        respostas[pid_str] = {}

    if resposta not in respostas[pid_str]:
        respostas[pid_str][resposta] = 0

    respostas[pid_str][resposta] += 1

    with open("data/respostas.json", "w", encoding="utf-8") as f:
        json.dump(respostas, f, ensure_ascii=False, indent=2)

    socketio.emit("nova_resposta", {
        "pergunta_id": pid,
        "resposta": resposta,
        "total": respostas[pid_str][resposta]
    }, broadcast=True)

    return jsonify({"status": "ok"})

@app.route("/responder-simples", methods=["POST"])
def responder_simples():
    data = request.json
    pergunta_id = str(data["id"])
    resposta = data["resposta"]

    try:
        with open("data/respostas.json", "r", encoding="utf-8") as f:
            respostas = json.load(f)
    except FileNotFoundError:
        respostas = {}

    if pergunta_id not in respostas:
        respostas[pergunta_id] = {}
    if resposta not in respostas[pergunta_id]:
        respostas[pergunta_id][resposta] = 0

    respostas[pergunta_id][resposta] += 1

    with open("data/respostas.json", "w", encoding="utf-8") as f:
        json.dump(respostas, f, indent=2, ensure_ascii=False)

    return jsonify({"status": "ok"})

@app.route("/resetar-respostas", methods=["POST"])
def resetar_respostas():
    with open("data/perguntas.json", "r", encoding="utf-8") as f:
        perguntas = json.load(f)

    respostas_resetadas = {
        str(p["id"]): {letra: 0 for letra in p["alternativas"].keys()}
        for p in perguntas
    }

    with open("data/respostas.json", "w", encoding="utf-8") as f:
        json.dump(respostas_resetadas, f, indent=2, ensure_ascii=False)

    return jsonify({"status": "respostas resetadas"})

@app.route("/resultado")
def resultado():
    email = session.get("email", "Desconhecido")

    with open("data/respostas.json", encoding="utf-8") as f:
        respostas = json.load(f)

    with open("data/perguntas.json", encoding="utf-8") as f:
        perguntas = json.load(f)

    return render_template("resultado.html", email=email, respostas=respostas, perguntas=perguntas)

@app.route("/api/editar/<int:pid>", methods=["POST"])
def editar_pergunta(pid):
    dados = request.get_json()

    with open("data/perguntas.json", "r", encoding="utf-8") as f:
        perguntas = json.load(f)

    for i, p in enumerate(perguntas):
        if p["id"] == pid:
            perguntas[i]["pergunta"] = dados.get("pergunta", p["pergunta"])
            perguntas[i]["alternativas"] = dados.get("alternativas", p["alternativas"])
            break
    else:
        return jsonify({"erro": "Pergunta não encontrada"}), 404

    with open("data/perguntas.json", "w", encoding="utf-8") as f:
        json.dump(perguntas, f, indent=2, ensure_ascii=False)

    return jsonify({"status": "pergunta editada"})

@app.route("/api/excluir/<int:pid>", methods=["DELETE"])
def excluir_pergunta(pid):
    with open("data/perguntas.json", "r", encoding="utf-8") as f:
        perguntas = json.load(f)

    perguntas = [p for p in perguntas if p["id"] != pid]

    with open("data/perguntas.json", "w", encoding="utf-8") as f:
        json.dump(perguntas, f, indent=2, ensure_ascii=False)

    return jsonify({"status": f"pergunta {pid} excluída"})

@app.route("/api/adicionar", methods=["POST"])
def adicionar_pergunta():
    dados = request.get_json()
    nova_pergunta = dados.get("pergunta")
    alternativas = dados.get("alternativas")
    correta = dados.get("correta")

    if not nova_pergunta or not alternativas or correta not in alternativas:
        return jsonify({"erro": "Dados inválidos"}), 400

    with open("data/perguntas.json", "r", encoding="utf-8") as f:
        perguntas = json.load(f)

    novo_id = max([p["id"] for p in perguntas], default=0) + 1

    nova = {
        "id": novo_id,
        "pergunta": nova_pergunta,
        "alternativas": alternativas,
        "correta": correta
    }

    perguntas.append(nova)

    with open("data/perguntas.json", "w", encoding="utf-8") as f:
        json.dump(perguntas, f, indent=2, ensure_ascii=False)

    try:
        with open("data/respostas.json", "r", encoding="utf-8") as f:
            respostas = json.load(f)
    except FileNotFoundError:
        respostas = {}

    respostas[str(novo_id)] = {letra: 0 for letra in alternativas.keys()}

    with open("data/respostas.json", "w", encoding="utf-8") as f:
        json.dump(respostas, f, indent=2, ensure_ascii=False)

    return jsonify({"status": "pergunta adicionada", "id": novo_id})

@app.route("/api/salvar-respostas", methods=["POST"])
def salvar_respostas():
    data = request.get_json()  # recebe JSON do frontend

    try:
        # tenta carregar as respostas anteriores
        with open("data/respostas_usuarios.json", "r", encoding="utf-8") as f:
            respostas = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        respostas = []

    respostas.append(data)  # adiciona nova resposta

    with open("data/respostas_usuarios.json", "w", encoding="utf-8") as f:
        json.dump(respostas, f, indent=2, ensure_ascii=False)

    return jsonify({"status": "resposta salva com sucesso"})


@app.route("/cadastrar", methods=["GET"])
def cadastrar_pergunta():
    if not session.get("admin_autenticado"):
        return redirect(url_for("admin"))
    return render_template("cadastrar.html")

@app.route("/static/perguntas.json")
def perguntas_estaticas():
    return send_from_directory("data", "perguntas.json")

@app.route("/api/respostas")
def api_respostas():
    try:
        with open("data/respostas.json", "r", encoding="utf-8") as f:
            respostas = json.load(f)
    except FileNotFoundError:
        respostas = {}

    return jsonify(respostas)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
