from firebase_init import db, SERVER_TIMESTAMP
import os
from dotenv import load_dotenv
import json
import fitz
import requests
from google.cloud import storage
from repositories.topic_repository import criar_topico_com_perguntas
from utils.enum import QuestionType
from utils.prompts import prompt_default, prompt_multiple_choice, prompt_short_answer, prompt_true_false

load_dotenv()

# Clave de API desde secrets de Replit
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
LLM_MODEL = "mistralai/mistral-7b-instruct:free"

def extract_text_from_pdf(pdf_url):
    response = requests.get(pdf_url)
    response.raise_for_status()

    doc = fitz.open(stream=response.content, filetype="pdf")

    text = ""
    for page in doc:
        text += page.get_text()

    return text

# def subir_a_gcs(nombre_archivo_local, nombre_bucket, nombre_destino):
#     client = storage.Client()
#     bucket = client.bucket(nombre_bucket)
#     blob = bucket.blob(nombre_destino)
#     blob.upload_from_filename(nombre_archivo_local)
#     print(f"✅ {nombre_archivo_local} subido a gs://{nombre_bucket}/{nombre_destino}")

# def descargar_de_gcs(nombre_remoto, nombre_bucket, nombre_local):
#     client = storage.Client()
#     bucket = client.bucket(nombre_bucket)
#     blob = bucket.blob(nombre_remoto)
#     blob.download_to_filename(nombre_local)
#     print(f"✅ {nombre_remoto} descargado de gs://{nombre_bucket} a {nombre_local}")
    
def generar_prompt_perguntas(texto, topico, qty, type):
    switch = {
        QuestionType.MULTIPLE_CHOICE: prompt_multiple_choice(topico, texto, qty),
        QuestionType.TRUE_FALSE: prompt_true_false(topico, texto, qty),
    }

    return switch.get(type, prompt_default)()

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


def guardar_preguntas_json(topic_name, topic_id, preguntas_str, guild_id, document_url):
    try:
        preguntas_novas = json.loads(preguntas_str)
    except json.JSONDecodeError:
        print("⚠️ Error al parsear JSON generado. Verifica el output del modelo.")
        return

    criar_topico_com_perguntas(guild_id, topic_name, topic_id, preguntas_novas, document_url)

    print(f"✅ {len(preguntas_novas)} preguntas guardadas en Firestore para el servidor {guild_id} y tópico '{topic_name}'")

    if os.path.exists("preguntas.json"):
        with open("preguntas.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    if topic_name not in data:
        data[topic_name] = []

    for i, pregunta in enumerate(preguntas_novas, start=1):
        pregunta["id"] = str(len(data[topic_name]) + i)
        data[topic_name].append(pregunta)

    with open("preguntas.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def generar_preguntas_desde_pdf(topic_name, topic_id, guild_id, pdf_url, qty, type):
    texto = extract_text_from_pdf(pdf_url)
    prompt = generar_prompt_perguntas(texto, topic_name, qty, type)
    resultado = enviar_a_openrouter(prompt)
    guardar_preguntas_json(topic_name, topic_id, resultado, guild_id, pdf_url)