import discord
from dotenv import load_dotenv
import os
from discord import app_commands

from utils.keep_alive import keep_alive
from utils.structured_logging import structured_logger as logger
from commands import questions_commands, quiz_commands, stats_commands, topics_commands
from repositories.server_repository import registrar_servidor, desativar_servidor, atualizar_ultima_interacao_servidor
from repositories.user_repository import register_single_user, registrar_usuarios_servidor
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
    logger.info(f"🆕 Bot added to server: {guild.name} (ID: {guild.id})",
               guild_id=str(guild.id),
               server_name=guild.name,
               operation="bot_guild_join")
    try:
        registrar_servidor(guild)
        registrar_usuarios_servidor(guild)
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
        desativar_servidor(guild.id)
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
        atualizar_ultima_interacao_servidor(interaction.guild.id)

        if is_professor(interaction):
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
        
        # Log de éxito del comando
        logger.info(f"✅ Comando /help completado exitosamente para {interaction.user.display_name}",
                   command="help",
                   user_id=str(interaction.user.id),
                   username=interaction.user.display_name,
                   guild_id=str(interaction.guild.id) if interaction.guild else None,
                   is_professor=is_professor(interaction),
                   operation="command_success")
    except Exception as e:
        logger.error(f"❌ Error en comando /help: {e}",
                    command="help",
                    user_id=str(interaction.user.id),
                    username=interaction.user.display_name,
                    guild_id=str(interaction.guild.id) if interaction.guild else None,
                    error_type=type(e).__name__,
                    error_message=str(e))
        
        # Usar followup porque ya hicimos defer
        try:
            await interaction.followup.send("❌ Error calling help.", ephemeral=True)
        except Exception:
            pass  # Si falla, al menos tenemos el log
        


keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
