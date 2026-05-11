import logging
import asyncio
import discord
from dotenv import load_dotenv
import os
from discord import app_commands

# Configure logging: suppress verbose discord.py logs, keep our custom logs clean
logging.basicConfig(
    level=logging.WARNING,  # Only show WARNING and above from all libraries
    format='%(asctime)s %(levelname)-8s %(name)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# Suppress noisy discord and aiohttp logs
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("discord.gateway").setLevel(logging.WARNING)
logging.getLogger("discord.client").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)

load_dotenv()

from utils.keep_alive import keep_alive
from utils.structured_logging import structured_logger as logger
from commands import questions_commands, quiz_commands, stats_commands, topics_commands, level_commands
from repositories.server_repository import register_server, deactivate_server, update_server_last_interaction, update_server_metadata
from repositories.user_repository import register_single_user, register_guild_users
from utils.utils import is_professor, log_command_event, interaction_has_admin_permission

DOCS_PATH = "docs"


def get_permission_label(interaction: discord.Interaction) -> str:
    labels = []
    if interaction_has_admin_permission(interaction):
        labels.append("admin")
    if is_professor(interaction):
        labels.append("faculty")

    return "|".join(labels) if labels else "member"


async def resolve_guild_name(interaction: discord.Interaction) -> str:
    guild_id = interaction.guild_id
    if interaction.guild and interaction.guild.name:
        return interaction.guild.name

    if guild_id:
        cached_guild = interaction.client.get_guild(guild_id)
        if cached_guild and cached_guild.name:
            return cached_guild.name

        try:
            fetched_guild = await interaction.client.fetch_guild(guild_id)
            if fetched_guild.name:
                return fetched_guild.name
        except discord.HTTPException:
            pass

    return "Unknown server"


async def format_command_log(interaction: discord.Interaction, command_name: str, status_icon: str) -> str:
    guild_id = interaction.guild_id
    guild_name = await resolve_guild_name(interaction)
    guild_id = guild_id if guild_id is not None else "N/A"
    user_label = f"{interaction.user} ({interaction.user.id})"
    permission_label = get_permission_label(interaction)
    return (
        f"{status_icon} Command Log\n"
        f"User: {user_label}\n"
        f"Permission: {permission_label}\n"
        f"Server: {guild_name} ({guild_id})\n"
        f"Command: /{command_name}"
    )


class QuizBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        super().__init__(intents=intents, reconnect=True, heartbeat_timeout=60)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            try:
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                print(f"🌍 Slash commands synced to guild {GUILD_ID}.")
            except discord.Forbidden:
                print(
                    f"⚠ Missing access to guild {GUILD_ID}. "
                    "Check DISCORD_GUILD_ID and that the bot is in that server. "
                    "Falling back to global sync."
                )
                await self.tree.sync()
                print("🌍 Slash commands synced globally.")
        else:
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
    configured_guild_id = int(os.getenv("DISCORD_GUILD_ID", "0"))
    connected_guild_ids = []

    for guild in bot.guilds:
        connected_guild_ids.append(guild.id)
        register_server(guild)

    print(f"✅ Bot connected as {bot.user}")
    if bot.guilds:
        for guild in bot.guilds:
            print(f"🏠 Connected guild: {guild.name} ({guild.id})")
    else:
        print("⚠ Bot is not connected to any guilds.")

    if configured_guild_id and configured_guild_id not in connected_guild_ids:
        print(
            f"⚠ DISCORD_GUILD_ID {configured_guild_id} is not in the connected guild list. "
            "Check that this bot token belongs to a bot invited to that server."
        )


@bot.event
async def on_disconnect():
    logging.warning("⚠ Bot disconnected. Trying to reconnect...")


@bot.event
async def on_resumed():
    logging.info("✅ Bot successfully reconnected!")


@bot.event
async def on_guild_join(guild: discord.Guild):
    log_command_event(
        "info", None,
        f"🆕 Bot added to server: {guild.name} (ID: {guild.id})",
        operation="bot_guild_join",
        guild_id=str(guild.id),
        guild_name=guild.name
    )
    try:
        register_server(guild)
        register_guild_users(guild)
        log_command_event(
            "info", None,
            f"📌 Server and users registered in Firestore: {guild.id}",
            operation="firestore_registration",
            guild_id=str(guild.id)
        )
    except Exception as e:
        log_command_event(
            "error", None,
            f"❌ Error registering server or users in Firestore: {e}",
            operation="firestore_registration",
            guild_id=str(guild.id),
            error_type=type(e).__name__
        )

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
    log_command_event(
        "info", None,
        f"👤 New user joined: {member.name} (ID: {member.id}) in server {member.guild.name}",
        operation="member_join",
        user_id=str(member.id),
        guild_id=str(member.guild.id),
        username=member.name
    )

    try:
        register_single_user(member.guild, member)
        update_server_metadata(member.guild)
    except Exception as e:
        log_command_event(
            "error", None,
            f"❌ Error registering new user {member.id}: {e}",
            operation="user_registration",
            user_id=str(member.id),
            guild_id=str(member.guild.id),
            error_type=type(e).__name__
        )

    channel = discord.utils.find(
        lambda c: c.permissions_for(
            member.guild.me).send_messages and isinstance(c, discord.TextChannel),
        member.guild.text_channels
    )
    if channel:
        await channel.send(f"👋 Welcome to the server, {member.mention}!")


@bot.event
async def on_member_remove(member: discord.Member):
    try:
        update_server_metadata(member.guild)
    except Exception as e:
        log_command_event(
            "warning", None,
            f"⚠️ Error updating server metadata after member leave: {e}",
            operation="server_metadata_update",
            guild_id=str(member.guild.id),
            error_type=type(e).__name__
        )


@bot.event
async def on_guild_remove(guild: discord.Guild):
    print(f"🔌 Bot removed from server: {guild.name} ({guild.id})")
    try:
        deactivate_server(guild.id)
    except Exception as e:
        print(f"❌ Error updating server status {guild.id}: {e}")


@bot.event
async def on_app_command_completion(interaction: discord.Interaction, command: discord.app_commands.Command):
    update_server_last_interaction(interaction.guild.id)

    if interaction.extras.get("command_failed"):
        print(await format_command_log(interaction, command.name, "⚠️"))
        log_command_event(
            "warning",
            interaction,
            "⚠️ Command finished with handled failure",
            operation="command_handled_failure"
        )
    else:
        print(await format_command_log(interaction, command.name, "✅"))
        log_command_event(
            "info",
            interaction,
            "✅ Command completed successfully",
            operation="command_success"
        )


@bot.event
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    update_server_last_interaction(interaction.guild.id)

    print(f"❌ Error in command {interaction.command.name}: {error}")

    log_command_event(
        "error",
        interaction,
        "❌ Command execution failed",
        operation="command_error",
        error_type=type(error).__name__,
        error_message=str(error)
    )

    try:
        await interaction.response.send_message("⚠️ An error occurred while executing this command.", ephemeral=True)
    except discord.InteractionResponded:
        await interaction.followup.send("⚠️ An error occurred while executing this command.", ephemeral=True)


async def global_command_check(interaction: discord.Interaction) -> bool:
    log_command_event(
        "info",
        interaction,
        "📢 Command called",
        operation="command_execution"
    )

    update_server_last_interaction(interaction.guild.id)
    await asyncio.sleep(0)
    return True


bot.tree.interaction_check = global_command_check


@bot.tree.command(name="help", description="Explains how to use the bot and its available commands")
async def help_command(interaction: discord.Interaction):
    try:
        if not interaction.response.is_done():
            await interaction.response.defer(thinking=True, ephemeral=True)

        if is_professor(interaction):
            message = (
                "📘 **Guide for Professors**\n\n"
                "👉 `/quiz <topic>` — Launch a 5-question quiz.\n\n"
                "👉 `/topics` — List the available topics to practice.\n"
                "👉 `/upload_pdf <topic> <file>` — Upload a PDF (no questions generated).\n"
                "👉 `/upload_topic <topic> <file>` — Upload a PDF and automatically generate True/False questions.\n\n"
                "👉 `/generate_questions <topic> <qty> <type>` — Generate multiple questions for a topic.\n"
                "👉 `/upload_questions_json <topic> <type> <file>` — Upload questions in bulk from a JSON file.\n"
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

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    except Exception as e:
        if isinstance(e, discord.HTTPException) and e.code in (40060, 10062):
            log_command_event(
                "warning",
                interaction,
                f"⚠ Ignoring duplicate or expired interaction in /help: {e}",
                operation="command_duplicate_interaction",
                error_type=type(e).__name__,
                error_message=str(e)
            )
            return

        log_command_event(
            "error",
            interaction,
            f"❌ Error in /help: {e}",
            operation="command_error",
            error_type=type(e).__name__,
            error_message=str(e)
        )
        try:
            await interaction.followup.send("❌ Error calling help.", ephemeral=True)
        except Exception:
            pass

keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
