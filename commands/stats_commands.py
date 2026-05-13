import logging
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import io
from discord import app_commands, Interaction, File
import discord

from repositories import stats_repository, quiz_repository
from repositories.server_repository import update_server_last_interaction
from utils.utils import is_professor, professor_verification, safe_defer
from utils.structured_logging import structured_logger as logger


INVALID_USER_NAMES = {
    "",
    "no_name",
    "no name",
    "unknown",
    "unknown user",
    "none",
    "null",
}

def register(tree: app_commands.CommandTree):

    @tree.command(name="stats", description="Shows a summary of the quizzes taken by all users (professors only)")
    @app_commands.default_permissions(administrator=True)
    async def stats(interaction: discord.Interaction):

        try:
            update_server_last_interaction(interaction.guild.id)

            if not await professor_verification(interaction):
                return

            if not await safe_defer(interaction, thinking=True, ephemeral=True):
                return

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
    @app_commands.default_permissions(administrator=True)
    async def user_stats(interaction: discord.Interaction):
        try:
            update_server_last_interaction(interaction.guild.id)

            if not await professor_verification(interaction):
                return

            # Defer early, since we're doing heavy processing
            if not await safe_defer(interaction, thinking=True, ephemeral=True):
                return

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

            labels = []
            passed_tests_by_user = {}
            failed_tests_by_user = {}
            label_counts = {}

            for uid, info in data.items():
                stored_name = str(info.get('name', '') or '').strip()
                normalized_name = stored_name.lower()
                display_name = stored_name

                # Replace placeholder names with the current guild display name when possible.
                if normalized_name in INVALID_USER_NAMES:
                    member = interaction.guild.get_member(int(uid))
                    if member is None:
                        try:
                            member = await interaction.guild.fetch_member(int(uid))
                        except Exception:
                            member = None

                    if member is not None:
                        display_name = member.display_name
                    else:
                        display_name = f"user_{uid}"

                attempts = info['attempts']
                passed_tests = 0
                failed_tests = 0

                for attempt in attempts:
                    success = attempt.get("success", 0)
                    failures = attempt.get("failures", 0)
                    total = success + failures

                    if total == 0:
                        continue

                    if (success / total) >= 0.5:
                        passed_tests += 1
                    else:
                        failed_tests += 1

                if passed_tests > 0 or failed_tests > 0:
                    label_counts[display_name] = label_counts.get(display_name, 0) + 1

                    if label_counts[display_name] > 1:
                        label = f"{display_name} ({str(uid)[-4:]})"
                    else:
                        label = display_name

                    labels.append(label)
                    passed_tests_by_user[label] = passed_tests
                    failed_tests_by_user[label] = failed_tests

            user_count = len(labels)
            total_attempts = sum(passed_tests_by_user.values()) + sum(failed_tests_by_user.values())

            fig, ax = plt.subplots(figsize=(12, 6))
            x_positions = list(range(len(labels)))
            width = 0.4
            passed_values = [passed_tests_by_user[label] for label in labels]
            failed_values = [failed_tests_by_user[label] for label in labels]

            success_positions = [x - width / 2 for x in x_positions]
            failure_positions = [x + width / 2 for x in x_positions]

            ax.bar(success_positions, passed_values, width=width, color='green', label='Passed tests')
            ax.bar(failure_positions, failed_values, width=width, color='red', label='Failed tests')

            max_value = max(passed_values + failed_values, default=0)
            upper_limit = ((max_value + 4) // 5 + 1) * 5

            ax.set_title('Quiz attempts per user')
            ax.set_ylabel('Number of attempts')
            ax.set_yticks(range(0, upper_limit + 1, 5))
            ax.set_xlabel('Users')
            ax.set_xticks(x_positions)
            ax.set_xticklabels(labels, rotation=45, ha='right')

            # Legend
            green_patch = mpatches.Patch(color='green', label='Passed tests')
            red_patch = mpatches.Patch(color='red', label='Failed tests')
            ax.legend(handles=[green_patch, red_patch])

            buf = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plt.close(fig)

            await interaction.followup.send(
                content="📊 Quiz attempts per user (green = passed, red = failed):",
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
    @app_commands.default_permissions(administrator=True)
    async def time_stats(interaction: discord.Interaction):
        try:
            update_server_last_interaction(interaction.guild.id)

            if not await professor_verification(interaction):
                return

            if not await safe_defer(interaction, thinking=True, ephemeral=True):
                return

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
