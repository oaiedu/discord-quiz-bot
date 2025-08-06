import discord
from dotenv import load_dotenv
import os
from discord import app_commands
import logging

from utils.keep_alive import keep_alive
from commands import questions_commands, quiz_commands, stats_commands, topics_commands
from repositories.server_repository import registrar_servidor, desativar_servidor, atualizar_ultima_interacao_servidor
from repositories.user_repository import registrar_usuarios_servidor
from utils.utils import is_professor

load_dotenv()
logging.basicConfig(level=logging.INFO)

RUTA_DOCS = "docs"
ROL_PROFESOR = "faculty"

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
questions_commands.register(bot.tree)
topics_commands.register(bot.tree)
quiz_commands.register(bot.tree)
stats_commands.register(bot.tree)


@bot.event
async def on_ready():
    print(f"\u2705 Bot conectado como {bot.user}")
    
@bot.event
async def on_guild_join(guild: discord.Guild):
    logging.info(f"🆕 Bot adicionado ao servidor: {guild.name} (ID: {guild.id})")
    try:
        registrar_servidor(guild)
        registrar_usuarios_servidor(guild)
        logging.info(f"📌 Servidor e usuários registrados no Firestore: {guild.id}")
    except Exception as e:
        logging.error(f"❌ Erro ao registrar servidor ou usuários no Firestore: {e}")

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
    try:
        desativar_servidor(guild.id)
    except Exception as e:
        print(f"❌ Erro ao atualizar status do servidor {guild.id}: {e}")


@bot.tree.command(name="help", description="Explica cómo usar el bot y sus comandos disponibles")
async def help_command(interaction: discord.Interaction):
    atualizar_ultima_interacao_servidor(interaction.guild.id)
    await interaction.response.defer(thinking=True, ephemeral=True)

    if is_professor:
        mensaje = (
            "📘 **Guía para profesores**\n\n"
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
            "📘 **Guía para estudiantes**\n\n"
            "👉 `/quiz <tema>` — Lanza un quiz de 5 preguntas de verdadero o falso.\n"
            "👉 `/topics` — Lista los temas disponibles para practicar.\n\n"
            "💬 Para responder un quiz, contesta con una secuencia como `VFVFV`.\n"
            "⏱️ Tienes 60 segundos para responder cada quiz.\n"
            "🧠 ¡Buena práctica!"
        )

    await interaction.followup.send(mensaje, ephemeral=True)


keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
