import os
import json
import fitz  # PyMuPDF
import requests

# Clave de API desde secrets de Replit
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
LLM_MODEL = "mistralai/mistral-7b-instruct:free"


def extract_text_from_pdf(pdf_path):
    text = ""
    doc = fitz.open(pdf_path)
    for page in doc:
        text += page.get_text()
    return text


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
        preguntas = json.loads(preguntas_str)
    except json.JSONDecodeError:
        print(
            "⚠️ Error al parsear JSON generado. Verifica el output del modelo."
        )
        return

    # Cargar preguntas existentes
    if os.path.exists("preguntas.json"):
        with open("preguntas.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    data[topico] = preguntas

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
