from firebase_init import db, SERVER_TIMESTAMP  # certifique-se que isso está no topo
import os
from dotenv import load_dotenv
import json
import fitz  # PyMuPDF
import requests
import uuid  # Adicione esta importação ao topo do arquivo
from google.cloud import storage

load_dotenv()

# Clave de API desde secrets de Replit
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
LLM_MODEL = "mistralai/mistral-7b-instruct:free"


def extract_text_from_pdf(pdf_path):
    text = ""
    doc = fitz.open(pdf_path)
    for page in doc:
        text += page.get_text()
    return text


def subir_a_gcs(nombre_archivo_local, nombre_bucket, nombre_destino):
    client = storage.Client()
    bucket = client.bucket(nombre_bucket)
    blob = bucket.blob(nombre_destino)
    blob.upload_from_filename(nombre_archivo_local)
    print(f"✅ {nombre_archivo_local} subido a gs://{nombre_bucket}/{nombre_destino}")

def descargar_de_gcs(nombre_remoto, nombre_bucket, nombre_local):
    client = storage.Client()
    bucket = client.bucket(nombre_bucket)
    blob = bucket.blob(nombre_remoto)
    blob.download_to_filename(nombre_local)
    print(f"✅ {nombre_remoto} descargado de gs://{nombre_bucket} a {nombre_local}")

def generar_prompt(texto, topico):
    return f"""
Eres un generador de preguntas. Basándote en el siguiente contenido, genera 50 preguntas de verdadero o falso.
Devuélvelas en formato JSON como este:
[
  {{ "pregunta": "...", "respuesta": "V" }},
  ...
]

Tema: {topico}

Contenido:
{texto[:4000]}  # limitamos para tokens, ajustable
"""


def enviar_a_openrouter(prompt):
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "Referer": "https://replit.com/@marcgc21",  # reemplázalo si quieres
            "X-Title": "Discord Quiz Bot"
        }

        payload = {
            "model": LLM_MODEL,
            "messages": [{
                "role": "user",
                "content": prompt
            }],
            "temperature": 0.7
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print("ERRO NO OPENROUTER", e)


def guardar_preguntas_json(topico, preguntas_str, guild_id, document_name, document_url):
    try:
        preguntas_novas = json.loads(preguntas_str)
    except json.JSONDecodeError:
        print("⚠️ Error al parsear JSON generado. Verifica el output del modelo.")
        return

    # 1️⃣ Criar o documento do tópico com ID autogerado
    topic_ref = db.collection("servers").document(str(guild_id)).collection("topics").document()
    topic_id = topic_ref.id  # ID gerado automaticamente

    # 2️⃣ Salvar os metadados do tópico
    topic_data = {
        "title": topico,
        "created_at": SERVER_TIMESTAMP,
        "document_name": document_name,
        "document_storage_url": document_url,
        "num_quizzes_generated": len(preguntas_novas)
    }
    topic_ref.set(topic_data)

    # 3️⃣ Adicionar perguntas como subdocumentos
    batch = db.batch()
    for idx, pregunta in enumerate(preguntas_novas):
        pregunta_id = str(idx + 1)
        doc_ref = topic_ref.collection("questions").document(pregunta_id)
        batch.set(doc_ref, {
            "pregunta": pregunta.get("pregunta", ""),
            "respuesta": pregunta.get("respuesta", "V")
        })
    batch.commit()

    print(f"✅ {len(preguntas_novas)} preguntas guardadas en Firestore para el servidor {guild_id} y tópico '{topico}'")

    # 4️⃣ Atualiza local preguntas.json
    if os.path.exists("preguntas.json"):
        with open("preguntas.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    if topico not in data:
        data[topico] = []

    for i, pregunta in enumerate(preguntas_novas, start=1):
        pregunta["id"] = str(len(data[topico]) + i)
        data[topico].append(pregunta)

    with open("preguntas.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def generar_preguntas_desde_pdf(topico, guild_id):
    pdf_path = os.path.join("docs", f"{topico}.pdf")

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"❌ No se encontró el archivo: {pdf_path}")

    texto = extract_text_from_pdf(pdf_path)
    prompt = generar_prompt(texto, topico)
    resultado = enviar_a_openrouter(prompt)
    guardar_preguntas_json(topico, resultado, guild_id, f"{topico.pdf}", "")

