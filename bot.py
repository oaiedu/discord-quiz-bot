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

DOCS_PATH = "docs"
ROLE_PROFESSOR = "faculty"


class QuizBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        super().__init__(intents=intents, reconnect=True, heartbeat_timeout=60)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # ⚡ Substitua pelo ID do servidor onde você testa o bot
        GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"🌍 Slash commands synced to guild {GUILD_ID}.")
        else:
            # fallback: sync global
            await self.tree.sync()
            print("🌍 Slash commands synced globally.")


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
    logging.warning("⚠ Bot disconnected. Trying to reconnect...")


@bot.event
async def on_resumed():
    logging.info("✅ Bot successfully reconnected!")


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

    channel = discord.utils.find(
        lambda c: c.permissions_for(
            guild.me).send_messages and isinstance(c, discord.TextChannel),
        guild.text_channels
    )

    if channel:
        await channel.send(
            "👋 Hello! Thanks for adding me to this server.\n"
            "Use `/help` to see how I can assist you with true or false quizzes. 🎓"
        )


@bot.event
async def on_member_join(member: discord.Member):
    logger.info(f"👤 New user joined: {member.name} (ID: {member.id}) in server {member.guild.name}",
                user_id=str(member.id),
                guild_id=str(member.guild.id),
                username=member.name,
                operation="member_join")

    try:
        register_single_user(member.guild, member)
    except Exception as e:
        logger.error(f"❌ Error registering new user {member.id}: {e}",
                     user_id=str(member.id),
                     guild_id=str(member.guild.id),
                     operation="user_registration",
                     error_type=type(e).__name__)

    channel = discord.utils.find(
        lambda c: c.permissions_for(
            member.guild.me).send_messages and isinstance(c, discord.TextChannel),
        member.guild.text_channels
    )
    if channel:
        await channel.send(f"👋 Welcome to the server, {member.mention}!")


@bot.event
async def on_guild_remove(guild: discord.Guild):
    print(f"🔌 Bot removed from server: {guild.name} ({guild.id})")
    try:
        deactivate_server(guild.id)
    except Exception as e:
        print(f"❌ Error updating server status {guild.id}: {e}")


@bot.tree.command(name="help", description="Explains how to use the bot and its available commands")
async def help_command(interaction: discord.Interaction):
    # Immediate DEFER to avoid Discord timeout (3 seconds)
    await interaction.response.defer(thinking=True, ephemeral=True)

    # Log the executed command with user information
    logger.info(f"🔍 Command /help executed by {interaction.user.display_name}",
                command="help",
                user_id=str(interaction.user.id),
                username=interaction.user.display_name,
                guild_id=str(
                    interaction.guild.id) if interaction.guild else None,
                guild_name=interaction.guild.name if interaction.guild else None,
                channel_id=str(
                    interaction.channel.id) if interaction.channel else None,
                is_professor=is_professor(interaction),
                operation="command_execution")

    try:
        update_server_last_interaction(interaction.guild.id)

        if is_professor(interaction):
            message = (
                "📘 **Guide for Professors**\n\n"
                "👉 `/quiz <topic>` — Launch a 5-question quiz.\n\n"
                "👉 `/topics` — List the available topics to practice.\n"
                "👉 `/upload_pdf <topic> <file>` — Upload a PDF (no questions generated).\n"
                "👉 `/upload_topic <topic> <file>` — Upload a PDF and automatically generate True/False questions.\n\n"
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
            message = (
                "📘 **Guide for Students**\n\n"
                "👉 `/quiz <topic>` — Take a 5-question quiz.\n"
                "👉 `/topics` — List all available quiz topics.\n"
                "👉 `/my_rank` — Show your XP and level.\n"
                "👉 `/rank` — Show the top 5 XP leaderboard.\n"
                "💬 To answer a quiz, click the button for each answer you think is correct."
                "⏱️ You have 60 seconds to answer each quiz.\n"
                "🧠 Happy practicing!"
            )

        await interaction.followup.send(message, ephemeral=True)

    except Exception as e:
        logger.error(f"❌ Error in /help: {e}")
        try:
            await interaction.followup.send("❌ Error calling help.", ephemeral=True)
        except Exception:
            pass

keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
