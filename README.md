# 🤖 ChatBot Zezinho – Corretora de Seguros

Auzeir é um assistente virtual simpático, educado e motivador que ajuda clientes de uma corretora de seguros a entender planos, tirar dúvidas e tomar decisões com confiança — tudo isso com muito bom humor e emojis! 😄

Este projeto integra:

- 🧠 **Groq + LLaMA 3.1** para respostas inteligentes
- 💬 **WhatsApp (Z-API)** para atendimento automatizado
- 🌐 **Flask** para interface web
- 🗃️ **PostgreSQL (Supabase)** para persistência de dados
- 🚀 **Deploy no Railway** (sem cartão de crédito!)

---

## 📦 Funcionalidades

- Pergunta nome, telefone, e-mail e CNPJ (se necessário)
- Recomenda planos de seguro com base no interesse
- Responde com mensagens curtas, motivadoras e cheias de emojis
- Armazena histórico e preferências no banco de dados
- Atende via WhatsApp e via navegador

---

## 🚀 Como rodar localmente

### 1. Clone o repositório

```bash
git clone https://github.com/Auzeir/ChatBot.git
cd ChatBot

2. Crie um ambiente virtual (opcional)

python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

3. Instale as dependências

pip install -r requirements.txt

4. Configure o .env
Crie um arquivo .env com as variáveis:

GROQ_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ZAPI_TOKEN=xxxxxxxxxxxxxxxxxxxx
ZAPI_INSTANCE_ID=xxxxxxxxxxxxxxxxxxxx
DB_HOST=db.xxxxx.supabase.co
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=sua_senha_aqui

5. Rode o app

python app.py
