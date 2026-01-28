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
from utils.utils import autocomplete_topics, is_professor, professor_verification, register_user_statistics, update_last_interaction


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
    @app_commands.describe(user_name="User full name")
    async def user_rank(interaction: discord.Interaction, user_name: str):
        try:
            update_last_interaction(interaction.guild.id)

            professor_verification(interaction)

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
