import logging
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import io
from discord import app_commands, Interaction, File
import discord

from repositories import stats_repository, quiz_repository
from repositories.server_repository import update_server_last_interaction
from utils.utils import is_professor, professor_verification
from utils.structured_logging import structured_logger as logger


def register(tree: app_commands.CommandTree):

    @tree.command(name="stats", description="Shows a summary of the quizzes taken by all users (professors only)")
    async def stats(interaction: discord.Interaction):

        try:
            update_server_last_interaction(interaction.guild.id)

            professor_verification(interaction)

            await interaction.response.defer(thinking=True, ephemeral=True)

            data = stats_repository.get_statistics_by_server(interaction.guild.id)

            if not data:
                logger.info("No statistics available for guild",
                            command="stats",
                            user_id=str(interaction.user.id),
                            username=interaction.user.name,
                            guild_id=str(interaction.guild.id),
                            operation="no_stats_found")
                await interaction.followup.send("📂 No statistics recorded yet.", ephemeral=True)
                return

            user_count = len(data)
            total_attempts = sum(len(info['attempts']) for info in data.values())

            summary = "📊 **Bot usage statistics:**\n"
            for uid, info in data.items():
                summary += f"\n👤 {info['name']}: {len(info['attempts'])} attempt(s)"
                for attempt in info['attempts'][-3:]:
                    summary += f"\n  • {attempt.get('topic_id', 'Unknown')}: {attempt.get('success', 0)}/{attempt.get('success', 0) + attempt.get('failures', 0)}"

            await interaction.followup.send(summary, ephemeral=True)

        except Exception as e:
            logging.error(f"Error retrieving statistics: {e}")

            try:
                await interaction.followup.send("❌ Error retrieving statistics.", ephemeral=True)
            except Exception:
                logging.error("Failed to send error message to user")
            
    @tree.command(name="user_stats", description="Shows a summary of quiz attempts per user (professors only)")
    async def user_stats(interaction: discord.Interaction):
        try:
            update_server_last_interaction(interaction.guild.id)

            professor_verification(interaction)

            # Defer early, since we're doing heavy processing
            await interaction.response.defer(thinking=True, ephemeral=True)

            data = stats_repository.get_statistics_by_server(
                interaction.guild.id)

            if not data:
                logger.info("No statistics available for guild",
                            command="user_stats",
                            user_id=str(interaction.user.id),
                            username=interaction.user.name,
                            guild_id=str(interaction.guild.id),
                            operation="no_stats_found")
                await interaction.followup.send("📂 No statistics recorded yet.", ephemeral=True)
                return

            names = []
            attempts_by_user = {}

            for uid, info in data.items():
                name = info['name']
                attempts = info['attempts']
                scores = []

                for attempt in attempts:
                    success = attempt.get("success", 0)
                    failures = attempt.get("failures", 0)
                    total = success + failures

                    if total == 0:
                        continue

                    avg = success / total
                    scores.append(avg)

                if scores:
                    names.append(name)
                    attempts_by_user[name] = scores

            user_count = len(names)
            total_attempts = sum(len(scores)
                                 for scores in attempts_by_user.values())

            fig, ax = plt.subplots(figsize=(12, 6))
            bottom_map = {name: 0 for name in names}

            for name in names:
                scores = attempts_by_user[name]
                for avg in scores:
                    color = 'green' if avg >= 0.5 else 'red'
                    ax.bar(name, 1, bottom=bottom_map[name], color=color)
                    bottom_map[name] += 1

            max_attempts = max(bottom_map.values(), default=0)
            upper_limit = ((max_attempts + 4) // 5 + 1) * 5

            ax.set_title('Quiz attempts per user')
            ax.set_ylabel('Number of attempts')
            ax.set_yticks(range(0, upper_limit + 1, 5))
            ax.set_xlabel('Users')
            plt.xticks(rotation=45, ha='right')

            # Legend
            green_patch = mpatches.Patch(color='green', label='≥ 50% correct')
            red_patch = mpatches.Patch(color='red', label='< 50% correct')
            ax.legend(handles=[green_patch, red_patch])

            buf = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plt.close(fig)

            await interaction.followup.send(
                content="📊 Quiz attempts per user (each bar segment = one attempt):",
                file=File(fp=buf, filename="user_stats_stacked.png"),
                ephemeral=True
            )

        except Exception as e:
            logging.error(f"Error generating user_stats graph: {e}")

            try:
                await interaction.followup.send("❌ Error retrieving statistics.", ephemeral=True)
            except Exception:
                logging.error("Failed to send error message to user")

    @tree.command(name="time_stats", description="Shows a summary of the quizzes taken over time (professors only)")
    async def time_stats(interaction: discord.Interaction):
        try:
            update_server_last_interaction(interaction.guild.id)

            professor_verification(interaction)

            await interaction.response.defer(thinking=True, ephemeral=True)

            temporal_data = quiz_repository.get_quizzes_by_period(
                interaction.guild.id)

            if not temporal_data:
                logger.info("No temporal statistics available for guild",
                            command="time_stats",
                            user_id=str(interaction.user.id),
                            username=interaction.user.name,
                            guild_id=str(interaction.guild.id),
                            operation="no_temporal_stats_found")
                await interaction.followup.send("📂 No statistics recorded yet.", ephemeral=True)
                return

            dates = list(temporal_data.keys())
            values = list(temporal_data.values())

            max_value = max(values, default=0)
            upper_limit = ((max_value + 4) // 5 + 1) * 5

            fig, ax = plt.subplots()
            ax.plot(dates, values, marker='o')
            ax.set_title('Quizzes over time')
            ax.set_xlabel('Date')
            ax.set_ylabel('Count')
            ax.set_yticks(range(0, upper_limit + 1, 5))
            plt.xticks(rotation=45)

            buf = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plt.close(fig)

            total_periods = len(dates)
            total_quizzes = sum(values)

            await interaction.followup.send(
                "📈 Statistics over time:",
                file=discord.File(fp=buf, filename="time_stats.png"),
                ephemeral=True
            )

        except Exception as e:
            logging.error(f"Error retrieving time statistics: {e}")

            try:
                await interaction.followup.send(f"❌ Error retrieving statistics. {e}", ephemeral=True)
            except Exception:
                logging.error("Failed to send error message to user")
