import discord
import os
from llm_utils import generar_preguntas_desde_pdf
import json
import random

RUTA_DOCS = "docs"


async def handle_upload(ctx, nombre_topico):
    if not ctx.message.attachments:
        await ctx.send(
            "❌ Por favor, adjunta un archivo PDF junto con el comando.")
        return

    archivo = ctx.message.attachments[0]

    if not archivo.filename.endswith(".pdf"):
        await ctx.send("❌ Solo se permiten archivos PDF.")
        return

    await ctx.send(
        f"📥 Recibiendo el archivo para el tema: **{nombre_topico}**...")

    os.makedirs(RUTA_DOCS, exist_ok=True)
    ruta_pdf = os.path.join(RUTA_DOCS, f"{nombre_topico}.pdf")
    await archivo.save(ruta_pdf)
    await ctx.send(
        f"✅ PDF guardado como `{nombre_topico}.pdf` en la carpeta `/docs`.")

    # Generar preguntas directamente en Replit
    try:
        generar_preguntas_desde_pdf(nombre_topico)
        await ctx.send("🧠 Preguntas generadas correctamente desde el PDF.")
    except Exception as e:
        await ctx.send(f"❌ Error al generar preguntas: {e}")


async def handle_quiz(ctx, nombre_topico):
    if not os.path.exists("preguntas.json"):
        await ctx.send("❌ No se encontró el archivo `preguntas.json`.")
        return

    with open("preguntas.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    if nombre_topico not in data:
        await ctx.send(
            f"❌ No hay preguntas registradas para el tema `{nombre_topico}`.")
        return

    preguntas = random.sample(data[nombre_topico],
                              min(10, len(data[nombre_topico])))

    texto_quiz = "📝 Responde con V o F (por ejemplo: `VFVFVFVFVF`):\n"
    for idx, p in enumerate(preguntas):
        texto_quiz += f"\n{idx+1}. {p['pregunta']}"

    await ctx.send(texto_quiz)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and len(
            m.content) == len(preguntas)

    try:
        respuesta = await ctx.bot.wait_for('message',
                                           check=check,
                                           timeout=60.0)
    except:
        await ctx.send("⏰ Tiempo agotado. Intenta nuevamente.")
        return

    resultado = "\n📊 Resultados:\n"
    correctas = 0
    for i, r in enumerate(respuesta.content.upper()):
        correcta = preguntas[i]['respuesta'].upper()
        if r == correcta:
            resultado += f"✅ {i+1}. Correcto\n"
            correctas += 1
        else:
            resultado += f"❌ {i+1}. Incorrecto (Respuesta correcta: {correcta})\n"

    resultado += f"\n🏁 Has acertado {correctas} de {len(preguntas)} preguntas."
    await ctx.send(resultado)
