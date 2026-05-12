import logging
import random
from discord import app_commands, Interaction, ButtonStyle
import discord
from discord.ui import View, Button
from firebase_admin import firestore

from repositories.level_repository import get_leaderboard, get_user_xp, get_user_xp_by_name
from repositories.question_repository import update_question_stats
from repositories.server_repository import update_server_last_interaction
from repositories.stats_repository import save_statistic
from repositories.topic_repository import get_questions_by_topic
from utils.enum import QuestionType
from utils.structured_logging import structured_logger as logger
from utils.utils import autocomplete_topics, is_professor, professor_verification, register_user_statistics, update_last_interaction, safe_defer

def _find_members_by_name(guild: discord.Guild, raw_input: str):
    query = (raw_input or "").strip()
    if not query:
        return []

    # Permite buscar por mención (<@123> / <@!123>) o por ID
    mention_id = query
    if query.startswith("<@") and query.endswith(">"):
        mention_id = query[2:-1].replace("!", "")

    if mention_id.isdigit():
        member = guild.get_member(int(mention_id))
        return [member] if member else []

    # 1) Coincidencia exacta
    exact = []
    for m in guild.members:
        if m.bot:
            continue
        if query in {m.name, m.display_name, (m.nick or "")}:
            exact.append(m)
    if exact:
        return exact

    # 2) Coincidencia exacta case-insensitive
    q = query.lower()
    ci_exact = []
    for m in guild.members:
        if m.bot:
            continue
        candidates = [m.name, m.display_name, (m.nick or "")]
        if any((c or "").lower() == q for c in candidates):
            ci_exact.append(m)

    return ci_exact

def register(tree: app_commands.CommandTree):

    @tree.command(name="rank", description="Show the top XP leaderboard in the server")
    async def global_rank(interaction: discord.Interaction):
        try:
            update_last_interaction(interaction.guild.id)

            leaderboard = get_leaderboard(str(interaction.guild.id), limit=5)
            leaderboard = get_leaderboard(str(interaction.guild.id), limit=5)
            if not leaderboard or len(leaderboard) == 0:
                await interaction.response.send_message(
                "📊 No leaderboard data available yet!\n"
                "Complete some quizzes to appear on the leaderboard.",
                ephemeral=True
            )
                return
            msg = "🏆 **Leaderboard**\n"
            for idx, (user_id, xp, level) in enumerate(leaderboard, start=1):
                user = await interaction.guild.fetch_member(user_id)
                msg += f"{idx}. {user.display_name} — {xp} XP (Level {level})\n"

            await interaction.response.send_message(msg)


        except Exception as e:
            await interaction.response.send_message(
                "❌ An error occurred while fetching the leaderboard.",
                ephemeral=True
            )

    @tree.command(name="my_rank", description="Show your XP and level")
    async def personal_rank(interaction: discord.Interaction):
        try:
            update_last_interaction(interaction.guild.id)

            xp, level = get_user_xp(
                str(interaction.user.id), str(interaction.guild.id))

            xp_for_next = 100 * level
            xp_current_level = xp - (100 * (level - 1))
            percent = int((xp_current_level / 100) * 10)
            bar = "🔵" * percent + "⚪" * (10 - percent)

            await interaction.response.send_message(
                f"**{interaction.user.display_name}**\n"
                f"Level {level} ({xp_current_level}/{100} XP)\n"
                f"{bar}",
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(
                "❌ An error occurred while fetching your rank.",
                ephemeral=True
            )

    @tree.command(name="user_rank", description="Display the specified user's rank")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(user_name="User full name")
    async def user_rank(interaction: discord.Interaction, user_name: str):
        if not await safe_defer(interaction, thinking=True, ephemeral=True):
            return

        try:
            if interaction.guild_id is None:
                await interaction.followup.send(
                    "⛔ This command can only be used inside a server.",
                    ephemeral=True
                )
                return

            update_last_interaction(interaction.guild_id)

            if not await professor_verification(interaction):
                return

            matches = _find_members_by_name(interaction.guild, user_name)

            if not matches:
                await interaction.followup.send(
                    f"❌ User '{user_name}' does not exist in this server.",
                    ephemeral=True
                )
                return

            if len(matches) > 1:
                names = ", ".join(m.display_name for m in matches[:5])
                await interaction.followup.send(
                    "⚠️ Multiple users match that name. Be more specific (use mention or exact username).\n"
                    f"Matches: {names}",
                    ephemeral=True
                )
                return

            target = matches[0]
            xp, level = get_user_xp(str(target.id), str(interaction.guild.id))

            level = max(1, int(level))
            xp_floor = 100 * (level - 1)
            xp_cap = 100 * level
            xp_current_level = max(0, xp - xp_floor)
            xp_needed = max(1, xp_cap - xp_floor)
            percent = min(10, max(0, int((xp_current_level / xp_needed) * 10)))
            bar = "🔵" * percent + "⚪" * (10 - percent)

            await interaction.followup.send(
                f"📊 Rank of {target.display_name}\n"
                f"Level {level} ({xp_current_level}/{xp_needed} XP)\n"
                f"{bar}",
                ephemeral=True
            )

        except Exception as e:
            logging.exception(f"Error in /user_rank: {e}")
            await interaction.followup.send(
                "❌ An error occurred while fetching the user's rank.",
                ephemeral=True
            )
