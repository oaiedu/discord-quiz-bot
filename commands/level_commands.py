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

    @tree.command(name="my_rank", description="Display your XP progress and level")
    async def my_rank(interaction: discord.Interaction):
        if not await safe_defer(interaction, thinking=True, ephemeral=True):
            return

        try:
            guild_id = interaction.guild_id
            if guild_id is None:
                await interaction.followup.send(
                    "⛔ This command can only be used inside a server.",
                    ephemeral=True
                )
                return

            try:
                update_last_interaction(guild_id)
            except Exception as e:
                logging.warning(f"Failed to update interaction: {e}")

            xp, level = get_user_xp(str(interaction.user.id), str(guild_id))

            level = max(1, int(level))
            xp_floor = 100 * (level - 1)
            xp_cap = 100 * level
            xp_in_level = max(0, xp - xp_floor)
            xp_needed = max(1, xp_cap - xp_floor)
            progress = min(10, max(0, int((xp_in_level / xp_needed) * 10)))
            bar = "🔵" * progress + "⚪" * (10 - progress)

            await interaction.followup.send(
                f"📊 Your Rank\n"
                f"Level {level} ({xp_in_level}/{xp_needed} XP)\n"
                f"{bar}",
                ephemeral=True
            )
        except Exception as e:
            logging.exception(f"Error in /my_rank: {e}")
            try:
                await interaction.followup.send(
                    "❌ An error occurred while fetching your rank.",
                    ephemeral=True
                )
            except Exception:
                pass

    @tree.command(name="user_rank", description="Display the specified user's rank")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(user_name="User full name")
    async def user_rank(interaction: discord.Interaction, user_name: str):
        try:
            update_last_interaction(interaction.guild.id)

            if not await professor_verification(interaction):
                return

            xp, level = get_user_xp_by_name(
                user_name, str(interaction.guild.id))

            xp_for_next = 100 * level
            xp_current_level = xp - (100 * (level - 1))
            percent = int((xp_current_level / xp_for_next) * 10)
            bar = "🔵" * percent + "⚪" * (10 - percent)

            await interaction.response.send_message(
                f"📊 Rank of **{user_name}**\n"
                f"Level {level} ({xp_current_level}/{xp_for_next} XP)\n"
                f"{bar}",
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(
                "❌ An error occurred while fetching the user's rank.",
                ephemeral=True
            )
