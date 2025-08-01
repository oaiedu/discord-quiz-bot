# Docker-ready entry point for Discord Bot (for Cloud Run)

import discord
from dotenv import load_dotenv
import os
import json
import random
from discord import app_commands
from utils.llm_utils import generar_preguntas_desde_pdf
import logging
from commands import crud_questions
from firebase_init import db, SERVER_TIMESTAMP
from utils.utils import actualizar_ultima_interaccion, registrar_user_estadistica

load_dotenv()

logging.basicConfig(level=logging.INFO)

RUTA_DOCS = "docs"
ROL_PROFESOR = "faculty"


def registrar_estadistica(usuario, topico, correctas, total):
    try:
        db.collection("estadisticas").add({
            "usuario_id": str(usuario.id),
            "nombre": usuario.name,
            "tema": topico,
            "correctas": correctas,
            "total": total,
            "timestamp": SERVER_TIMESTAMP
        })
    except Exception as e:
        logging.error(f"Erro ao registrar estatística: {e}")


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
        print("\U0001F310 Slash commands sincronizados.")


bot = QuizBot()

crud_questions.register(bot.tree)


@bot.event
async def on_ready():
    print(f"\u2705 Bot conectado como {bot.user}")


@bot.tree.command(
    name="stats",
    description="Muestra un resumen de los quizzes realizados por todos los usuarios (solo profesores)"
)
async def estadisticas(interaction: discord.Interaction):
    actualizar_ultima_interaccion(interaction.guild.id)

    if not any(role.name.lower() == ROL_PROFESOR.lower()
               for role in interaction.user.roles):
        await interaction.response.send_message(
            "\u26d4 Este comando solo está disponible para profesores.",
            ephemeral=True)
        return

    try:
        docs = db.collection("estadisticas").stream()
        datos = {}
        for doc in docs:
            item = doc.to_dict()
            uid = item.get("usuario_id")
            if uid not in datos:
                datos[uid] = {"nombre": item.get("nombre"), "intentos": []}
            datos[uid]["intentos"].append(item)

        if not datos:
            await interaction.response.send_message("\ud83d\udcc2 No hay estadísticas registradas todavía.")
            return

        resumen = "\ud83d\udcca **Estadísticas de uso del bot:**\n"
        for uid, info in datos.items():
            resumen += f"\n\U0001F464 {info['nombre']}: {len(info['intentos'])} intento(s)"
            for intento in info['intentos'][-3:]:
                resumen += f"\n  • {intento['tema']}: {intento['correctas']}/{intento['total']}"

        await interaction.response.send_message(resumen)
    except Exception as e:
        logging.error(f"Erro ao obter estadísticas: {e}")
        await interaction.response.send_message("❌ Erro ao obter estadísticas.")


@bot.tree.command(name="upload", description="Sube un PDF y genera preguntas automáticamente")
@app_commands.describe(
    nombre_topico="Nombre del tema para guardar el PDF",
    archivo="Archivo PDF con el contenido"
)
async def upload(interaction: discord.Interaction, nombre_topico: str, archivo: discord.Attachment):
    actualizar_ultima_interaccion(interaction.guild.id)

    await interaction.response.defer(thinking=True)

    if not archivo.filename.endswith(".pdf"):
        await interaction.followup.send("❌ Solo se permiten archivos PDF.")
        return

    os.makedirs(RUTA_DOCS, exist_ok=True)
    ruta_pdf = os.path.join(RUTA_DOCS, f"{nombre_topico}.pdf")
    await archivo.save(ruta_pdf)

    try:
        guild_id = interaction.guild.id
        generar_preguntas_desde_pdf(nombre_topico, guild_id)
        await interaction.followup.send("\U0001F9E0 Preguntas generadas correctamente desde el PDF.")
    except Exception as e:
        await interaction.followup.send(f"❌ Error al generar preguntas: {e}")


@bot.tree.command(name="topics", description="Muestra los temas disponibles para hacer quizzes")
async def topics(interaction: discord.Interaction):
    actualizar_ultima_interaccion(interaction.guild.id)
    try:
        temas_docs = db.collection("servers") \
                       .document(str(interaction.guild.id)) \
                       .collection("topics") \
                       .get()
        
        if not temas_docs:
            await interaction.response.send_message("❌ No hay temas disponibles todavía.")
            return
        
        temas = "\n".join(f"- {doc.id}" for doc in temas_docs)
        await interaction.response.send_message(f"📚 Temas disponibles:\n{temas}")
    except Exception as e:
        logging.error(f"Erro ao carregar tópicos: {e}")
        await interaction.response.send_message("❌ Erro ao carregar os temas.")

async def obtener_temas_autocompletado(interaction: discord.Interaction, current: str):
    try:
        docs = db.collection("servers") \
                 .document(str(interaction.guild.id)) \
                 .collection("topics") \
                 .get()

        # Extrair os nomes dos tópicos (IDs dos documentos)
        nomes_temas = [doc.id for doc in docs]

        resultados = [
            app_commands.Choice(name=nome, value=nome)
            for nome in nomes_temas if current.lower() in nome.lower()
        ][:25]  # limitar a 25 sugestões como recomendado pelo Discord

        return resultados
    except Exception as e:
        logging.error(f"Erro ao obter temas para autocompletar: {e}")
        return []


@bot.tree.command(name="quiz", description="Haz un quiz de 5 preguntas sobre un tema")
@app_commands.describe(nombre_topico="Nombre del tema")
@app_commands.autocomplete(nombre_topico=obtener_temas_autocompletado)
async def quiz(interaction: discord.Interaction, nombre_topico: str):
    if interaction.guild:
        actualizar_ultima_interaccion(interaction.guild.id)

    try:
        preguntas_ref = db.collection("servers") \
                          .document(str(interaction.guild.id)) \
                          .collection("topics") \
                          .document(nombre_topico) \
                          .collection("questions")
        
        docs = preguntas_ref.stream()
        preguntas_data = [doc.to_dict() for doc in docs]

        if not preguntas_data:
            await interaction.response.send_message(f"❌ No hay preguntas registradas para el tema `{nombre_topico}`.")
            return

        preguntas = random.sample(preguntas_data, min(5, len(preguntas_data)))
        texto_quiz = "\ud83d\udcdd Responde con V o F (por ejemplo: `VFVFV`):\n"
        for idx, p in enumerate(preguntas):
            texto_quiz += f"\n{idx+1}. {p['pregunta']}"

        await interaction.response.send_message(texto_quiz)

        def check(m):
            return (
                m.author == interaction.user and
                m.channel.id == interaction.channel_id and
                len(m.content.strip()) == len(preguntas)
            )

        try:
            respuesta = await bot.wait_for("message", check=check, timeout=60.0)
            respuesta_str = respuesta.content.strip().upper()
        except:
            await interaction.followup.send("⏰ Tiempo agotado. Intenta nuevamente.")
            return

        resultado = "\n\ud83d\udcca Resultados:\n"
        correctas = 0
        for i, r in enumerate(respuesta_str):
            correcta = preguntas[i]['respuesta'].upper()
            if r == correcta:
                resultado += f"✅ {i+1}. Correcto\n"
                correctas += 1
            else:
                resultado += f"❌ {i+1}. Incorrecto (Respuesta correcta: {correcta})\n"

        resultado += f"\n\U0001F3C1 Has acertado {correctas} de {len(preguntas)} preguntas."
        await interaction.followup.send(resultado)

        registrar_user_estadistica(interaction.user, nombre_topico, correctas, len(preguntas))

    except Exception as e:
        logging.error(f"Erro ao realizar quiz: {e}")
        await interaction.response.send_message("❌ Ocurrió un error durante el quiz.")

@bot.tree.command(name="help", description="Explica cómo usar el bot y sus comandos disponibles")
async def help_command(interaction: discord.Interaction):
    actualizar_ultima_interaccion(interaction.guild.id)

    await interaction.response.defer(thinking=True, ephemeral=True)

    es_profe = False
    if interaction.guild:
        member = interaction.user
        es_profe = any(role.name.lower() == ROL_PROFESOR.lower() for role in member.roles)

    if es_profe:
        mensaje = (
            "\ud83d\udcd8 **Guía para profesores**\n\n"
            "👉 `/quiz <tema>` — Lanza un quiz de 5 preguntas de verdadero o falso.\n"
            "👉 `/topics` — Lista los temas disponibles para practicar.\n"
            "👉 `/upload <tema>` — Sube un PDF para generar nuevas preguntas.\n"
            "👉 `/stats` — Consulta los resultados de todos los estudiantes.\n"
            "👉 `/add_question`, `/list_questions`, `/delete_question` — Gestión manual de preguntas.\n\n"
            "💬 Para responder un quiz, contesta con una secuencia como `VFVFV`.\n"
            "⏱️ Tienes 60 segundos para responder cada quiz.\n"
            "🧠 ¡Buena práctica!"
        )
    else:
        mensaje = (
            "\ud83d\udcd8 **Guía para estudiantes**\n\n"
            "👉 `/quiz <tema>` — Lanza un quiz de 5 preguntas de verdadero o falso.\n"
            "👉 `/topics` — Lista los temas disponibles para practicar.\n\n"
            "💬 Para responder un quiz, contesta con una secuencia como `VFVFV`.\n"
            "⏱️ Tienes 60 segundos para responder cada quiz.\n"
            "🧠 ¡Buena práctica!"
        )

    await interaction.followup.send(mensaje, ephemeral=True)


@bot.event
async def on_guild_join(guild: discord.Guild):
    logging.info(f"🆕 Bot adicionado ao servidor: {guild.name} (ID: {guild.id})")

    try:
        db.collection("servers").document(str(guild.id)).set({
            "owner_id": str(guild.owner_id),
            "server_id": str(guild.id),
            "joined_at": SERVER_TIMESTAMP,
            "status": "Active"
        })

        # Adiciona cada membro à subcoleção 'usuarios'
        for member in guild.members:
            if member.bot:
                continue  # Ignora bots
            db.collection("servers") \
              .document(str(guild.id)) \
              .collection("users") \
              .document(str(member.id)) \
              .set({
                  "user_id": str(member.id),
                  "name": member.name,
                  "joined_bot_at": SERVER_TIMESTAMP
              })
        
        logging.info(f"📌 Servidor e usuários registrados no Firestore: {guild.id}")

    except Exception as e:
        logging.error(f"❌ Erro ao registrar servidor ou usuários no Firestore: {e}")

    # Envia mensagem de boas-vindas no primeiro canal disponível
    canal = discord.utils.find(
        lambda c: c.permissions_for(guild.me).send_messages and isinstance(c, discord.TextChannel),
        guild.text_channels
    )

    if canal:
        await canal.send(
            "👋 ¡Hola! Gracias por añadirme a este servidor.\n"
            "Usa `/help` para ver cómo puedo ayudarte com quizzes de verdadero o falso. 🎓"
        )

@bot.event
async def on_guild_remove(guild: discord.Guild):
    print(f"🔌 Bot removido do servidor: {guild.name} ({guild.id})")

    # Atualiza o campo 'status' no Firestore
    try:
        db.collection("servers").document(str(guild.id)).update({
            "status": "disabled"
        })
        print(f"📁 Status do servidor {guild.id} atualizado para 'disabled'")
    except Exception as e:
        print(f"❌ Erro ao atualizar status do servidor {guild.id}: {e}")        

from utils.keep_alive import keep_alive

keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
