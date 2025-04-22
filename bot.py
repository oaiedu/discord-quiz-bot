# Docker-ready entry point for Discord Bot (for Cloud Run)

import discord
import os
import json
import random
from discord import app_commands
from llm_utils import generar_preguntas_desde_pdf, subir_a_gcs, descargar_de_gcs

RUTA_DOCS = "docs"
RUTA_ESTADISTICAS = "estadisticas.json"
ROL_PROFESOR = "faculty"


def registrar_estadistica(usuario, topico, correctas, total):
    datos = {}
    if os.path.exists(RUTA_ESTADISTICAS):
        with open(RUTA_ESTADISTICAS, "r", encoding="utf-8") as f:
            datos = json.load(f)
    uid = str(usuario.id)
    if uid not in datos:
        datos[uid] = {"nombre": usuario.name, "intentos": []}
    datos[uid]["intentos"].append({
        "tema": topico,
        "correctas": correctas,
        "total": total
    })
    with open(RUTA_ESTADISTICAS, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)


class QuizBot(discord.Client):

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print("🌐 Slash commands sincronizados.")


bot = QuizBot()


@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    if not os.path.exists("preguntas.json"):
        try:
            descargar_de_gcs("preguntas.json", os.getenv("GCS_BUCKET_NAME"), "preguntas.json")
            print("📥 preguntas.json descargado desde GCS.")
        except Exception as e:
            print(f"⚠️ No se pudo descargar preguntas.json: {e}")


@bot.tree.command(
    name="stats",
    description=
    "Muestra un resumen de los quizzes realizados por todos los usuarios (solo profesores)"
)
async def estadisticas(interaction: discord.Interaction):
    if not any(role.name.lower() == ROL_PROFESOR.lower()
               for role in interaction.user.roles):
        await interaction.response.send_message(
            "⛔ Este comando solo está disponible para profesores.",
            ephemeral=True)
        return
    if not os.path.exists(RUTA_ESTADISTICAS):
        await interaction.response.send_message(
            "📂 No hay estadísticas registradas todavía.")
        return
    with open(RUTA_ESTADISTICAS, "r", encoding="utf-8") as f:
        datos = json.load(f)
    resumen = "📊 **Estadísticas de uso del bot:**\n"
    for uid, info in datos.items():
        resumen += f"\n👤 {info['nombre']}: {len(info['intentos'])} intento(s)"
        for intento in info['intentos'][-3:]:
            resumen += f"\n  • {intento['tema']}: {intento['correctas']}/{intento['total']}"
    await interaction.response.send_message(resumen)


@bot.tree.command(name="upload", description="Sube un PDF y genera preguntas automáticamente")
@app_commands.describe(
    nombre_topico="Nombre del tema para guardar el PDF",
    archivo="Archivo PDF con el contenido"
)
async def upload(interaction: discord.Interaction, nombre_topico: str, archivo: discord.Attachment):
    await interaction.response.defer(thinking=True)

    if not archivo.filename.endswith(".pdf"):
        await interaction.followup.send("❌ Solo se permiten archivos PDF.")
        return

    os.makedirs(RUTA_DOCS, exist_ok=True)
    ruta_pdf = os.path.join(RUTA_DOCS, f"{nombre_topico}.pdf")
    await archivo.save(ruta_pdf)

    try:
        generar_preguntas_desde_pdf(nombre_topico)
        subir_a_gcs("preguntas.json", os.getenv("GCS_BUCKET_NAME"), "preguntas.json")
        await interaction.followup.send("🧠 Preguntas generadas correctamente desde el PDF.")
    except Exception as e:
        await interaction.followup.send(f"❌ Error al generar preguntas: {e}")



@bot.tree.command(name="topics",
                  description="Muestra los temas disponibles para hacer quizzes")
async def topics(interaction: discord.Interaction):
    if not os.path.exists("preguntas.json"):
        await interaction.response.send_message(
            "❌ No se encontró el archivo `preguntas.json`.")
        return
    with open("preguntas.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    if not data:
        await interaction.response.send_message(
            "❌ No hay temas disponibles todavía.")
        return
    temas = "\n".join(f"- {t}" for t in data.keys())
    await interaction.response.send_message(f"📚 Temas disponibles:\n{temas}")


async def obtener_temas_autocompletado(interaction: discord.Interaction, current: str):
    if not os.path.exists("preguntas.json"):
        return []
    with open("preguntas.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    return [
        app_commands.Choice(name=tema, value=tema)
        for tema in data.keys() if current.lower() in tema.lower()
    ][:25]  # Discord permite hasta 25 opciones



@bot.tree.command(name="quiz",
                  description="Haz un quiz de 5 preguntas sobre un tema")
@app_commands.describe(nombre_topico="Nombre del tema")
@app_commands.autocomplete(nombre_topico=obtener_temas_autocompletado)
async def quiz(interaction: discord.Interaction, nombre_topico: str):
    if not os.path.exists("preguntas.json"):
        await interaction.response.send_message(
            "❌ No se encontró el archivo `preguntas.json`.")
        return
    with open("preguntas.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    if nombre_topico not in data:
        await interaction.response.send_message(
            f"❌ No hay preguntas registradas para el tema `{nombre_topico}`.")
        return
    preguntas = random.sample(data[nombre_topico], min(5, len(data[nombre_topico])))
    texto_quiz = "📝 Responde con V o F (por ejemplo: `VFVFV`):\n"
    for idx, p in enumerate(preguntas):
        texto_quiz += f"\n{idx+1}. {p['pregunta']}"
    await interaction.response.send_message(texto_quiz)

    def check(m):
        return (m.author == interaction.user and m.channel.id == interaction.channel_id and len(m.content.strip()) == len(preguntas))

    try:
        respuesta = await bot.wait_for("message", check=check, timeout=60.0)
        respuesta_str = respuesta.content.strip().upper()
    except:
        await interaction.followup.send("⏰ Tiempo agotado. Intenta nuevamente.")
        return

    resultado = "\n📊 Resultados:\n"
    correctas = 0
    for i, r in enumerate(respuesta_str):
        correcta = preguntas[i]['respuesta'].upper()
        if r == correcta:
            resultado += f"✅ {i+1}. Correcto\n"
            correctas += 1
        else:
            resultado += f"❌ {i+1}. Incorrecto (Respuesta correcta: {correcta})\n"
    resultado += f"\n🏁 Has acertado {correctas} de {len(preguntas)} preguntas."
    await interaction.followup.send(resultado)
    registrar_estadistica(interaction.user, nombre_topico, correctas, len(preguntas))


@bot.tree.command(name="help",
                  description="Explica cómo usar el bot y sus comandos disponibles")
async def help_command(interaction: discord.Interaction):
    es_profe = False
    if interaction.guild:
        member = interaction.user
        es_profe = any(role.name.lower() == ROL_PROFESOR.lower() for role in member.roles)

    if es_profe:
        mensaje = (
            "📘 **Guía para profesores**\n\n"
            "👉 `/quiz <tema>` — Lanza un quiz de 5 preguntas de verdadero o falso.\n"
            "👉 `/topics` — Lista los temas disponibles para practicar.\n"
            "👉 `/upload <tema>` — Sube un PDF para generar nuevas preguntas.\n"
            "👉 `/stats` — Consulta los resultados de todos los estudiantes.\n\n"
            "💬 Para responder un quiz, contesta con una secuencia como `VFVFV`.\n"
            "⏱️ Tienes 60 segundos para responder cada quiz.\n"
            "🧠 ¡Buena práctica!")
    else:
        mensaje = (
            "📘 **Guía para estudiantes**\n\n"
            "👉 `/quiz <tema>` — Lanza un quiz de 5 preguntas de verdadero o falso.\n"
            "👉 `/topics` — Lista los temas disponibles para practicar.\n\n"
            "💬 Para responder un quiz, contesta con una secuencia como `VFVFV`.\n"
            "⏱️ Tienes 60 segundos para responder cada quiz.\n"
            "🧠 ¡Buena práctica!")

    await interaction.response.send_message(mensaje, ephemeral=True)


from keep_alive import keep_alive

keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
