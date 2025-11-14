from flask import Flask, request, render_template, session
import os, requests, psycopg2, unicodedata, random, time
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = "zezinho-seguro"

# Escolhe o arquivo com base no ambiente
env_file = ".env.production" if os.getenv("RAILWAY_ENV") == "true" else ".env.local"
load_dotenv(env_file)


# Configurações
ASSISTENTE_NAME = "Auzeir"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ZAPI_URL = f"https://api.z-api.io/instances/{os.getenv('ZAPI_INSTANCE_ID')}/token/{os.getenv('ZAPI_TOKEN')}/send-message"

DB_CONF = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT")
}
if DB_CONF["host"] not in ["localhost", "127.0.0.1"]:
    DB_CONF["sslmode"] = "require"

conn = psycopg2.connect(**DB_CONF)
cursor = conn.cursor()


# Criação das tabelas
cursor.execute("""
CREATE TABLE IF NOT EXISTS clientes_seg (
    id SERIAL PRIMARY KEY,
    nome TEXT,
    email TEXT UNIQUE,
    telefone TEXT UNIQUE,
    idade TEXT,
    cnpj TEXT,
    ultima_interacao TEXT
);
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS serviços_seg (
    id SERIAL PRIMARY KEY,
    nome TEXT,
    preco REAL
);
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS memoria_seg (
    id SERIAL PRIMARY KEY,
    cliente_nome TEXT,
    chave TEXT,
    valor TEXT
);
""")
conn.commit()

# Funções auxiliares
def normalizar(txt):
    txt = txt.lower()
    txt = unicodedata.normalize('NFD', txt)
    txt = ''.join(c for c in txt if unicodedata.category(c) != 'Mn')
    for p in ".,;:!?":
        txt = txt.replace(p, "")
    return txt.strip()

def formatar_preco(p):
    try:
        v = float(str(p).replace("R$", "").replace(",", ".").strip())
        return f"R$ {v:.2f}"
    except:
        return str(p)

def responder_com_groq(mensagem):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": f"""
Você é {ASSISTENTE_NAME}, um assistente virtual de uma corretora de seguros.
Seja cordial, educado e alegre 😄. Use emojis para deixar a conversa leve e motivadora.
Ajude o cliente a entender os serviços, tirar dúvidas e tomar decisões com confiança.
Sempre incentive a adesão aos planos com frases positivas e acolhedoras.
**SEMPRE COM RESPOSTAS CURTAS** motivando o cliente para instigar o cliente a aderir os serviços.
Começar perguntando o nome.
Depois perguntar se o número que está entrando em contato é dele mesmo e se pode salvá-lo.
Depois perguntar o e-mail, caso o cliente demonstrar interesse depois pergunta o CNPJ.
Não ser repetitivo.
"""},
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
        return f"🤖 {ASSISTENTE_NAME}: Hmm... não entendi. Pode repetir? 🤔"
    except Exception as e:
        print("Erro:", e)
        return f"🤖 {ASSISTENTE_NAME}: Algo deu errado. Vamos de novo? 🤞"
    
    
    # Funções de memória
def salvar_memoria(nome, chave, valor):
    cursor.execute(
        "INSERT INTO memoria_seg (cliente_nome, chave, valor) VALUES (%s, %s, %s)",
        (nome, chave, valor)
    )
    conn.commit()

def recuperar_memoria(nome, chave):
    cursor.execute(
        "SELECT valor FROM memoria_seg WHERE cliente_nome=%s AND chave=%s ORDER BY id DESC LIMIT 1",
        (nome, chave)
    )
    r = cursor.fetchone()
    return r[0] if r else None

def marcar_pendente(nome, v): salvar_memoria(nome, "pendente", v)
def limpar_pendente(nome): salvar_memoria(nome, "pendente", "")

# Sugestão de serviços

def recomendar_servicos():
    cursor.execute("SELECT tipo, cobertura, valor FROM serviços_seg ORDER BY id LIMIT 5")
    return cursor.fetchall()

def consultar_servicos():
    cursor.execute("SELECT tipo, cobertura, valor FROM serviços_seg ORDER BY id")
    return cursor.fetchall()

# Interface de terminal
def bot(msg, aleatorio=True):
    print(f"\n🤖 {ASSISTENTE_NAME}: {msg}")
    time.sleep(1)
    if aleatorio and random.random() < 0.3:
        print(f"🤖 {ASSISTENTE_NAME}: {random.choice(['Claro! 😊','Boa escolha! 😍','Adorei! 👊','Tô contigo! 🚀'])}")
        time.sleep(1)

def user_input(prompt):
    return input(f"\n🧑 Você: {prompt} ").strip()


# Rota principal web

@app.route("/", methods=["GET"])
def home():
    session.clear()
    session["etapa"] = "inicio"
    session["contexto"] = ""
    resposta = f"Olá! 👋 Seja muito bem-vindo(a) à nossa corretora de seguros!\nSou o {ASSISTENTE_NAME}, seu consultor virtual 🧢💼.\nAntes de tudo, qual é seu nome completo?"
    return render_template("index.html", resposta=resposta)


@app.route("/chat", methods=["POST"])
def chat_web():
    mensagem = request.form.get("mensagem", "").strip()
    etapa = session.get("etapa", "nome")
    nome = session.get("nome", "")
    contexto = session.get("contexto", "")
    
    if etapa == "inicio":
        session["etapa"] = "nome"
        resposta = "Antes de tudo, qual é seu nome completo?"    

    if etapa == "nome":
        nome = mensagem.title()
        session["nome"] = nome

        # Verifica se o nome já está na base
        cursor.execute("SELECT telefone, email, cnpj FROM clientes_seg WHERE nome ILIKE %s LIMIT 1", (nome,))
        cliente = cursor.fetchone()

        if cliente:
            session["etapa"] = "atualizar"
            resposta = f"Bem-vindo(a) de volta, {nome.split()[0]}! 😄 Que bom te ver por aqui de novo!\nDeseja atualizar seus dados de contato?"
        else:
            session["etapa"] = "telefone"
            resposta = f"Prazer, {nome.split()[0]}! 😄 Esse número que você está usando é seu mesmo? Posso salvá-lo?"
    elif etapa == "atualizar":
        if "sim" in mensagem.lower():
            session["etapa"] = "telefone"
            resposta = "📱 Qual seu telefone com DDD?"
        else:
            session["etapa"] = "final"
            resposta = "Perfeito! 😄 Já posso te mostrar os planos disponíveis. Vamos lá!"
    elif etapa == "telefone":
        session["telefone"] = mensagem
        session["etapa"] = "email"
        resposta = "📧 Qual seu e-mail para que eu possa te enviar os planos disponíveis?"
    elif etapa == "email":
        session["email"] = mensagem.lower()
        session["etapa"] = "interesse"
        resposta = "Você está buscando seguro pessoal ou empresarial? 🏠🏢"
    elif etapa == "interesse":
        interesse = normalizar(mensagem)
        if "empresa" in interesse:
            session["etapa"] = "cnpj"
            resposta = "Se for empresarial, me manda o CNPJ por gentileza 🏢"
        else:
            session["etapa"] = "final"
            resposta = "Perfeito! 😄 Já posso te mostrar os planos disponíveis. Vamos lá!"
    elif etapa == "cnpj":
        session["etapa"] = "final"
        resposta = "Obrigado! Agora vamos ver os planos disponíveis pra você 😄"
    else:
        resposta = responder_com_groq(f"{contexto}\nCliente: {mensagem}")

    contexto += f"\nCliente: {mensagem}\n{ASSISTENTE_NAME}: {resposta}"
    session["contexto"] = contexto
    return render_template("index.html", resposta=resposta)

# Webhook para WhatsApp
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

    if not nome:
        resposta = f"Olá! 👋 Sou o {ASSISTENTE_NAME}, seu consultor virtual 🧢💼.\nQual é seu nome completo?"
    elif any(p in texto_normalizado for p in ["plano", "seguro", "cobertura", "proteção", "serviço"]):
        servicos = consultar_servicos()
        if servicos:
            resposta = "💼 Aqui estão nossos seguros disponíveis:\n\n"
            for tipo, cobertura, valor in servicos:
                resposta += f"🔹 {tipo}\n📄 {cobertura}\n💰 {valor}\n\n"
        else:
            resposta = "Ainda não temos serviços cadastrados. Volte em breve! ⏳"
    else:
        resposta = responder_com_groq(f"Cliente: {user_text}")

    requests.post(ZAPI_URL, json={"phone": phone, "message": resposta})
    return "ok", 200

if __name__ == "__main__":
    app.run(port=5000, debug=True)
