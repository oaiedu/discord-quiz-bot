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
        print("\U0001F310 Slash commands synchronized.")


bot = QuizBot()
questions_commands.register(bot.tree)
topics_commands.register(bot.tree)
quiz_commands.register(bot.tree)
stats_commands.register(bot.tree)


@bot.event
async def on_ready():
    print(f"\u2705 Bot connected as {bot.user}")
    
@bot.event
async def on_guild_join(guild: discord.Guild):
    logging.info(f"🆕 Bot added to server: {guild.name} (ID: {guild.id})")
    try:
        registrar_servidor(guild)
        registrar_usuarios_servidor(guild)
        logging.info(f"📌 Server and users registered in Firestore: {guild.id}")
    except Exception as e:
        logging.error(f"❌ Error registering server or users in Firestore: {e}")

    canal = discord.utils.find(
        lambda c: c.permissions_for(guild.me).send_messages and isinstance(c, discord.TextChannel),
        guild.text_channels
    )

    if canal:
        await canal.send(
            "👋 Hello! Thanks for adding me to this server.\n"
            "Use `/help` to see how I can assist you with true or false quizzes. 🎓"
        )

@bot.event
async def on_guild_remove(guild: discord.Guild):
    print(f"🔌 Bot removed from server: {guild.name} ({guild.id})")
    try:
        desativar_servidor(guild.id)
    except Exception as e:
        print(f"❌ Error updating server status {guild.id}: {e}")


@bot.tree.command(name="help", description="Explains how to use the bot and its available commands")
async def help_command(interaction: discord.Interaction):
    atualizar_ultima_interacao_servidor(interaction.guild.id)
    await interaction.response.defer(thinking=True, ephemeral=True)

    if is_professor:
        mensaje = (
            "📘 **Guide for Professors**\n\n"
            "👉 `/quiz <topic>` — Launch a 5-question true or false quiz.\n"
            "👉 `/topics` — List the available topics to practice.\n"
            "👉 `/upload <topic>` — Upload a PDF to generate new questions.\n"
            "👉 `/stats` — View the results of all students.\n"
            "👉 `/add_question`, `/list_questions`, `/delete_question` — Manage questions manually.\n\n"
            "💬 To answer a quiz, respond with a sequence like `TFTFT`.\n"
            "⏱️ You have 60 seconds to answer each quiz.\n"
            "🧠 Happy practicing!"
        )
    else:
        mensaje = (
            "📘 **Guide for Students**\n\n"
            "👉 `/quiz <topic>` — Launch a 5-question true or false quiz.\n"
            "👉 `/topics` — List the available topics to practice.\n\n"
            "💬 To answer a quiz, respond with a sequence like `TFTFT`.\n"
            "⏱️ You have 60 seconds to answer each quiz.\n"
            "🧠 Happy practicing!"
        )

    await interaction.followup.send(mensaje, ephemeral=True)


keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
