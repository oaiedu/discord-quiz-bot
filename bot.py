import logging
import discord
from dotenv import load_dotenv
import os
from discord import app_commands

from utils.keep_alive import keep_alive
from utils.structured_logging import structured_logger as logger
from commands import questions_commands, quiz_commands, stats_commands, topics_commands, level_commands
from repositories.server_repository import register_server, deactivate_server, update_server_last_interaction
from repositories.user_repository import register_single_user, register_guild_users
from utils.utils import is_professor

load_dotenv()

RUTA_DOCS = "docs"
ROL_PROFESOR = "faculty"

class QuizBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        super().__init__(intents=intents, reconnect=True, heartbeat_timeout=60)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print("\U0001F310 Slash commands synchronized.")

bot = QuizBot()
questions_commands.register(bot.tree)
topics_commands.register(bot.tree)
quiz_commands.register(bot.tree)
stats_commands.register(bot.tree)
level_commands.register(bot.tree)

@bot.event
async def on_ready():
    print(f"\u2705 Bot connected as {bot.user}")

@bot.event
async def on_disconnect():
    logging.warning("⚠ Bot desconectado. Tentando reconectar...")

@bot.event
async def on_resumed():
    logging.info("✅ Bot reconectado com sucesso!")

@bot.event
async def on_guild_join(guild: discord.Guild):
    logger.info(f"🆕 Bot added to server: {guild.name} (ID: {guild.id})",
               guild_id=str(guild.id),
               server_name=guild.name,
               operation="bot_guild_join")
    try:
        register_server(guild)
        register_guild_users(guild)
        logger.info(f"📌 Server and users registered in Firestore: {guild.id}",
                   guild_id=str(guild.id),
                   operation="firestore_registration")
    except Exception as e:
        logger.error(f"❌ Error registering server or users in Firestore: {e}",
                    guild_id=str(guild.id),
                    operation="firestore_registration",
                    error_type=type(e).__name__)

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
async def on_member_join(member: discord.Member):
    logger.info(f"👤 Novo usuário entrou: {member.name} (ID: {member.id}) no servidor {member.guild.name}",
               user_id=str(member.id),
               guild_id=str(member.guild.id),
               username=member.name,
               operation="member_join")

    try:
        register_single_user(member.guild, member)
    except Exception as e:
        logger.error(f"❌ Erro ao registrar novo usuário {member.id}: {e}",
                    user_id=str(member.id),
                    guild_id=str(member.guild.id),
                    operation="user_registration",
                    error_type=type(e).__name__)

    canal = discord.utils.find(
        lambda c: c.permissions_for(member.guild.me).send_messages and isinstance(c, discord.TextChannel),
        member.guild.text_channels
    )
    if canal:
        await canal.send(f"👋 Bem-vindo(a) ao servidor, {member.mention}!")

@bot.event
async def on_guild_remove(guild: discord.Guild):
    print(f"🔌 Bot removed from server: {guild.name} ({guild.id})")
    try:
        deactivate_server(guild.id)
    except Exception as e:
        print(f"❌ Error updating server status {guild.id}: {e}")

@bot.tree.command(name="help", description="Explains how to use the bot and its available commands")
async def help_command(interaction: discord.Interaction):
    # DEFER INMEDIATO para evitar timeout de Discord (3 segundos)
    await interaction.response.defer(thinking=True, ephemeral=True)
    
    # Log del comando ejecutado con información del usuario
    logger.info(f"🔍 Comando /help ejecutado por {interaction.user.display_name}",
               command="help",
               user_id=str(interaction.user.id),
               username=interaction.user.display_name,
               guild_id=str(interaction.guild.id) if interaction.guild else None,
               guild_name=interaction.guild.name if interaction.guild else None,
               channel_id=str(interaction.channel.id) if interaction.channel else None,
               is_professor=is_professor(interaction),
               operation="command_execution")
    
    try:
        update_server_last_interaction(interaction.guild.id)

        if is_professor(interaction):
            mensaje = (
                "📘 **Guide for Professors**\n\n"
                "👉 `/quiz <topic>` — Launch a 5-question quiz.\n\n"
                "👉 `/topics` — List the available topics to practice.\n"
                "👉 `/upload_pdf <topic> <file>` — Upload a PDF (no questions generated).\n"
                "👉 `/upload_topic <topic> <file>` — Upload a PDF and automatically generate questions True/False.\n\n"
                "👉 `/generate_questions <topic> <qty> <type>` — Generate multiple questions for a topic.\n"
                "👉 `/add_question` — Add a question manually.\n"
                "👉 `/list_questions <topic>` — List all questions in a topic.\n"
                "👉 `/delete_question <topic> <id>` — Delete a specific question.\n\n"
                "👉 `/stats` — View global quiz results.\n"
                "👉 `/user_stats` — See quiz stats per student.\n"
                "👉 `/time_stats` — View quiz history over time.\n\n"
                "👉 `/my_rank` — Show your XP and level.\n"
                "👉 `/rank` — Show the top 5 XP leaderboard.\n"
                "👉 `/user_rank <name>` — Show another user's rank.\n\n"
                "💬 To answer a quiz, click the button for each answer you think is correct."
                "⏱️ You have 60 seconds to answer each quiz.\n"
                "🧠 Happy teaching!"
            )
        else:
            mensaje = (
                "📘 **Guide for Students**\n\n"
                "👉 `/quiz <topic>` — Take a 5-question quiz.\n"
                "👉 `/topics` — List all available quiz topics.\n"
                "👉 `/my_rank` — Show your XP and level.\n"
                "👉 `/rank` — Show the top 5 XP leaderboard.\n"
                "💬 To answer a quiz, click the button for each answer you think is correct."
                "⏱️ You have 60 seconds to answer each quiz.\n"
                "🧠 Happy practicing!"
            )

        await interaction.followup.send(mensaje, ephemeral=True)

    except Exception as e:
        logger.error(f"❌ Error in /help: {e}")
        try:
            await interaction.followup.send("❌ Error calling help.", ephemeral=True)
        except Exception:
            pass

keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
