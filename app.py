import os
import time
import random
import unicodedata
import requests
import psycopg2
from flask import Flask, request, render_template
from dotenv import load_dotenv

load_dotenv()

# Configurações
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}/send-text"
ASSISTENTE_NAME = os.getenv("ASSISTENTE_NAME")



DB_CONF = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT"),
    "sslmode": "require"
}

# Conexão com banco
conn = psycopg2.connect(**DB_CONF)
cursor = conn.cursor()

# Flask app
app = Flask(__name__)
contexto_web = ""

# Funções auxiliares
def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("ASCII")
    return texto.lower().strip()

def responder_com_groq(mensagem):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                "content": """
Você é {ASSISTENTE_NAME}, um assistente virtual de uma corretora de seguros. 
Seja cordial, educado e alegre 😄. Use emojis para deixar a conversa leve e motivadora.
Ajude o cliente a entender os serviços, tirar dúvidas e tomar decisões com confiança.
Sempre incentive a adesão aos planos com frases positivas e acolhedoras.
**SEMPRE COM RESPOSTAS CURTAS** motivando o cliente para instigar o cliente a aderir os serviços.
Começar perguntando o nome.
Depois perguntar se o número que está entrando em contato é dele mesmo e se pode salvá-lo.
Depois perguntar o e-mail, caso o cliente demonstrar interesse depois pergunta o CNPJ.
Não ser repetitivo.
"""
            },
            {"role": "user", "content": mensagem}
        ],
        "temperature": 0.7
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        r.raise_for_status()
        d = r.json()
        if d.get("choices"):
            return d["choices"][0]["message"]["content"]
        if d.get("error"):
            return f"⚠️ Erro da IA: {d['error'].get('message','')}"
        return "🤖 {ASSISTENTE_NAME}: Hmm... não entendi. Pode repetir? 🤔"
    except Exception as e:
        print("Erro:", e)
        return "🤖 {ASSISTENTE_NAME}: Algo deu errado. Vamos de novo? 🤞"

def salvar_memoria(nome, chave, valor):
    cursor.execute("INSERT INTO memoria_seg (nome, chave, valor) VALUES (%s, %s, %s)", (nome, chave, valor))
    conn.commit()

def consultar_servicos():
    cursor.execute("SELECT tipo, cobertura, valor FROM serviços_seg ORDER BY id")
    return cursor.fetchall()

# Rota web principal
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat_web():
    global contexto_web
    mensagem = request.form.get("mensagem", "")
    resposta = responder_com_groq(f"{contexto_web}\nCliente: {mensagem}")
    contexto_web += f"\nCliente: {mensagem}\n{ASSISTENTE_NAME}: {resposta}"
    return render_template("index.html", resposta=resposta)

# Webhook WhatsApp
@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    data = request.get_json()
    if "message" not in data:
        return "mensagem ausente", 400

    msg = data["message"]
    user_text = msg["body"]
    phone = msg["from"]
    texto_normalizado = normalizar(user_text)

    cursor.execute("SELECT nome FROM clientes_seg WHERE telefone=%s LIMIT 1", (phone,))
    r = cursor.fetchone()
    nome = r[0] if r else None

    ENCERRAMENTO = ["não", "nao", "tá bom", "por enquanto é só", "só isso", "valeu", "obrigado", "agradeço"]

    if any(p in texto_normalizado for p in ENCERRAMENTO):
        resposta = "Fechado! 😄 Foi um prazer te ajudar. Se precisar, é só chamar! 👋💼"
    elif any(p in texto_normalizado for p in ["plano", "seguro", "cobertura", "proteção", "serviço"]):
        servicos = consultar_servicos()
        if servicos:
            resposta = "💼 Aqui estão nossos seguros disponíveis:\n\n"
            for tipo, cobertura, valor in servicos:
                resposta += f"🔹 {tipo}\n📄 {cobertura}\n💰 {valor}\n\n"
        else:
            resposta = "Ainda não temos serviços cadastrados. Volte em breve! ⏳"
    elif not nome:
        resposta = "Olá! 👋 Seja bem-vindo à nossa corretora de seguros!\nSou o {ASSISTENTE_NAME} 🧢💼. Qual é seu nome completo?"
    else:
        resposta = responder_com_groq(f"Cliente: {user_text}")

    requests.post(ZAPI_URL, json={"phone": phone, "message": resposta})
    return "ok", 200

if __name__ == "__main__":
    app.run(port=5000, debug=True)