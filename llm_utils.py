import os
import json
import fitz  # PyMuPDF
import requests
import uuid  # Adicione esta importação ao topo do arquivo
from google.cloud import storage

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


def guardar_preguntas_json(topico, preguntas_str):
    try:
        preguntas_novas = json.loads(preguntas_str)
    except json.JSONDecodeError:
        print("⚠️ Error al parsear JSON generado. Verifica el output del modelo.")
        return

    # Carregar perguntas existentes
    if os.path.exists("preguntas.json"):
        with open("preguntas.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    if topico not in data:
        data[topico] = []

    # Determinar o próximo ID incremental
    perguntas_existentes = data[topico]
    ultimo_id = max(
        [int(q["id"]) for q in perguntas_existentes if "id" in q and str(q["id"]).isdigit()],
        default=0
    )

    for i, pregunta in enumerate(preguntas_novas, start=1):
        pregunta["id"] = str(ultimo_id + i)

    # Atualizar os dados com as novas perguntas
    data[topico].extend(preguntas_novas)

    with open("preguntas.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def generar_preguntas_desde_pdf(topico):
    pdf_path = os.path.join("docs", f"{topico}.pdf")

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"❌ No se encontró el archivo: {pdf_path}")

    texto = extract_text_from_pdf(pdf_path)
    prompt = generar_prompt(texto, topico)
    resultado = enviar_a_openrouter(prompt)
    guardar_preguntas_json(topico, resultado)
