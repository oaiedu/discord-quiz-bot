import logging
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import io
from discord import app_commands, Interaction, File
import discord

from repositories import stats_repository, quiz_repository
from repositories.server_repository import update_server_last_interaction
from utils.utils import is_professor, professor_verification, safe_defer, autocomplete_all_topics
from repositories.topic_repository import get_questions_by_topic
from utils.structured_logging import structured_logger as logger


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

    
    @tree.command(name="topic_stats", description="Shows detailed statistics for a topic (professors only)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(topic="Topic name")
    @app_commands.autocomplete(topic=autocomplete_all_topics)
    async def topic_stats(interaction: discord.Interaction, topic: str):
        try:
            update_server_last_interaction(interaction.guild.id)

            if not await professor_verification(interaction):
                return

            if not await safe_defer(interaction, thinking=True, ephemeral=True):
                return

            question_docs = get_questions_by_topic(interaction.guild.id, topic)

            if not question_docs:
                logger.info("No topic statistics available for topic",
                            command="topic_stats",
                            user_id=str(interaction.user.id),
                            username=interaction.user.name,
                            guild_id=str(interaction.guild.id),
                            topic=topic,
                            operation="no_topic_stats_found")
                await interaction.followup.send(
                    f"📂 No question statistics were found for topic '{topic}'.",
                    ephemeral=True,
                )
                return

            question_stats = []
            total_success = 0
            total_failures = 0

            for doc in question_docs:
                data = doc.to_dict() or {}
                question_text = data.get("question", "Untitled question")
                success = int(data.get("success", 0) or 0)
                failures = int(data.get("failures", 0) or 0)

                total_success += success
                total_failures += failures

                question_stats.append({
                    "question": question_text,
                    "success": success,
                    "failures": failures,
                })

            total_answers = total_success + total_failures
            global_success_rate = (
                total_success / total_answers if total_answers > 0 else 0
            )

            def _conclusion_by_rate(rate: float) -> str:
                if rate < 0.25:
                    return "Needs urgent reinforcement"
                if rate < 0.5:
                    return "Below expectations"
                if rate < 0.75:
                    return "On the right track"
                return "Excellent mastery"

            top_success = sorted(
                question_stats,
                key=lambda q: q["success"],
                reverse=True
            )[:3]
            top_failures = sorted(
                question_stats,
                key=lambda q: q["failures"],
                reverse=True
            )[:3]

            report = [
                "📊 **Topic Statistics Report**",
                f"**Topic:** {topic}",
                f"**Total correct answers:** {total_success}",
                f"**Total wrong answers:** {total_failures}",
                f"**Total answers:** {total_answers}",
                f"**Global success rate:** {global_success_rate * 100:.2f}%",
                "",
                "**Top 3 questions with most correct answers:**"
            ]

            if any(item["success"] > 0 for item in top_success):
                for index, item in enumerate(top_success, start=1):
                    snippet = item["question"][:120]
                    suffix = "..." if len(item["question"]) > 120 else ""
                    report.append(
                        f"{index}. ({item['success']} correct) {snippet}{suffix}"
                    )
            else:
                report.append("1. No correct-answer data yet.")

            report.append("")
            report.append("**Top 3 questions with most wrong answers:**")

            if any(item["failures"] > 0 for item in top_failures):
                for index, item in enumerate(top_failures, start=1):
                    snippet = item["question"][:120]
                    suffix = "..." if len(item["question"]) > 120 else ""
                    report.append(
                        f"{index}. ({item['failures']} wrong) {snippet}{suffix}"
                    )
            else:
                report.append("1. No wrong-answer data yet.")

            report.append("")
            report.append(
                f"**Auto conclusion:** {_conclusion_by_rate(global_success_rate)}"
            )

            if total_answers > 0:
                pie_fig, pie_ax = plt.subplots(figsize=(6, 6))
                pie_ax.pie(
                    [total_success, total_failures],
                    labels=["Correct", "Wrong"],
                    colors=["green", "red"],
                    autopct="%1.1f%%",
                    startangle=90,
                    wedgeprops={"edgecolor": "white", "linewidth": 1},
                )
                pie_ax.set_title("Correct vs Wrong Answers")
                pie_ax.axis("equal")

                pie_buf = io.BytesIO()
                pie_fig.tight_layout()
                pie_fig.savefig(pie_buf, format="png")
                pie_buf.seek(0)
                plt.close(pie_fig)

                await interaction.followup.send(
                    "\n".join(report),
                    file=discord.File(fp=pie_buf, filename="topic_stats_pie.png"),
                    ephemeral=True,
                )
            else:
                report.append("\nNo answers yet, so the pie chart is not available.")
                await interaction.followup.send("\n".join(report), ephemeral=True)

        except Exception as e:
            logging.error(f"Error retrieving topic statistics: {e}")

            try:
                await interaction.followup.send("❌ Error retrieving topic statistics.", ephemeral=True)
            except Exception:
                logging.error("Failed to send error message to user")
