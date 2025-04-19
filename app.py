import os, time
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
THREAD_MAP = {}

app = Flask(__name__)

print("🔑 OPENAI_API_KEY:", os.getenv("OPENAI_API_KEY") is not None)
print("🤖 ASSISTANT_ID:", ASSISTANT_ID)


def run_assistant(user_id: str, text: str) -> str:
    # 1) Cria ou recupera thread_id para manter contexto
    if user_id not in THREAD_MAP:
        thread = client.beta.threads.create(metadata={"wa": user_id})
        THREAD_MAP[user_id] = thread.id
    thread_id = THREAD_MAP[user_id]

    # 2) Envia a mensagem do usuário ao PrediBot
    client.beta.threads.messages.create(thread_id=thread_id, role="user", content=text)

    # 3) Inicia o run no assistant especificado
    run = client.beta.threads.runs.create(
        thread_id=thread_id, assistant_id=ASSISTANT_ID
    )

    # 4) Poll até completar
    while run.status not in ("completed", "failed"):
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
    print("⏱️ Run concluido: ", run)
    # 5) Recupera todas as mensagens e encontra a última do assistant
    msgs = client.beta.threads.messages.list(thread_id=thread_id).data
    print("📜 Mensagens: ", [(m.role, m.content) for m in msgs])
    for m in reversed(msgs):
        if m.role == "assistant":
            # retorna o texto gerado
            return m.content[0].text.value

    if run.status == "failed":
        return f"⚠️ PrediBot falhou: {getattr(run, 'error', 'sem detalhes')}"


@app.route("/whats", methods=["POST"])
def inbound_whatsapp():
    user = request.values.get("From")  # ex.: "whatsapp:+55..."
    text = request.values.get("Body")
    answer = run_assistant(user, text)  # usa a implementação acima

    resp = MessagingResponse()
    resp.message(answer)
    return str(resp)


if __name__ == "__main__":
    app.run(port=5000)
