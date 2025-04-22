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


@bot.tree.command(name="upload",
                  description="Sube un PDF y genera preguntas automáticamente")
@app_commands.describe(
    nombre_topico="Nombre del tema para guardar el PDF y generar preguntas")
async def upload(interaction: discord.Interaction, nombre_topico: str):
    if not interaction.attachments:
        await interaction.response.send_message(
            "❌ Por favor, adjunta un archivo PDF.")
        return
    archivo = interaction.attachments[0]
    if not archivo.filename.endswith(".pdf"):
        await interaction.response.send_message(
            "❌ Solo se permiten archivos PDF.")
        return
    await interaction.response.send_message(
        f"📥 Recibiendo el archivo para el tema: **{nombre_topico}**...")
    os.makedirs(RUTA_DOCS, exist_ok=True)
    ruta_pdf = os.path.join(RUTA_DOCS, f"{nombre_topico}.pdf")
    await archivo.save(ruta_pdf)
    try:
        generar_preguntas_desde_pdf(nombre_topico)
        # Guardar en Google Cloud Storage
        subir_a_gcs("preguntas.json", os.getenv("GCS_BUCKET_NAME"), "preguntas.json")
        await interaction.followup.send(
            "🧠 Preguntas generadas correctamente desde el PDF.")
    except Exception as e:
        await interaction.followup.send(f"❌ Error al generar preguntas: {e}")


# Resto del archivo permanece igual...

from keep_alive import keep_alive

keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
