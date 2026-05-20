import logging
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import io
from discord import app_commands, Interaction, File
import discord

from repositories import stats_repository, quiz_repository
from repositories.server_repository import update_server_last_interaction
from utils.utils import is_professor, professor_verification, safe_defer, autocomplete_all_topics
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

    @tree.command(name="topic_stats", description="Muestra estadísticas detalladas de un tópico (solo profesorado)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(topic="Nombre del tópico")
    @app_commands.autocomplete(topic=autocomplete_all_topics)
    async def topic_stats(interaction: discord.Interaction, topic: str):
        try:
            if interaction.guild_id is None:
                await interaction.response.send_message(
                    "⛔ Este comando solo puede usarse dentro de un servidor.",
                    ephemeral=True
                )
                return

            update_server_last_interaction(interaction.guild_id)

            if not await professor_verification(interaction):
                return

            if not await safe_defer(interaction, thinking=True, ephemeral=True):
                return

            data = stats_repository.get_topic_statistics(interaction.guild_id, topic)

            if not data:
                await interaction.followup.send(
                    f"📂 No se encontró el tópico '{topic}' o no hay datos disponibles.",
                    ephemeral=True
                )
                return

            def short_question(text: str, limit: int = 90):
                return text if len(text) <= limit else text[:limit - 3] + "..."

            top_success_lines = []
            for i, q in enumerate(data["top_success_questions"], start=1):
                top_success_lines.append(
                    f"{i}. {short_question(q['question'])} ({q['success']} aciertos)"
                )

            top_failure_lines = []
            for i, q in enumerate(data["top_failure_questions"], start=1):
                top_failure_lines.append(
                    f"{i}. {short_question(q['question'])} ({q['failures']} fallos)"
                )

            if not top_success_lines:
                top_success_lines.append("Sin datos suficientes.")
            if not top_failure_lines:
                top_failure_lines.append("Sin datos suficientes.")

            msg = (
                f"📊 Estadísticas del tópico\n\n"
                f"Topico: {data['topic']}\n"
                f"Total aciertos: {data['total_success']}\n"
                f"Total fallos: {data['total_failures']}\n"
                f"Total respuestas: {data['total_answers']}\n"
                f"% acierto global: {data['accuracy']:.2f}%\n\n"
                f"Top 3 preguntas con más aciertos:\n" + "\n".join(top_success_lines) + "\n\n"
                f"Top 3 preguntas con más fallos:\n" + "\n".join(top_failure_lines) + "\n\n"
                f"Conclusión: {data['conclusion']}"
            )

            # --- Pie chart: correct vs failed ---
            fig, ax = plt.subplots(figsize=(5, 5))

            correct = data["total_success"]
            failed = data["total_failures"]
            total = data["total_answers"]

            if total > 0:
                sizes = [correct, failed]
                labels = ["Aciertos", "Fallos"]
                colors = ["#2E8B57", "#C0392B"]

                ax.pie(
                    sizes,
                    labels=labels,
                    colors=colors,
                    autopct="%1.1f%%",
                    startangle=90,
                    wedgeprops={"edgecolor": "white", "linewidth": 1.2}
                )
                ax.set_title(f"Distribucion de respuestas - {data['topic']}")
            else:
                # Evita error de matplotlib cuando todo es 0
                ax.pie(
                    [1],
                    labels=["Sin respuestas"],
                    colors=["#95A5A6"],
                    startangle=90,
                    wedgeprops={"edgecolor": "white", "linewidth": 1.2}
                )
                ax.set_title(f"Distribucion de respuestas - {data['topic']}")

            ax.axis("equal")

            buf = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buf, format="png", dpi=150)
            buf.seek(0)
            plt.close(fig)

            await interaction.followup.send(
                content=msg,
                file=File(fp=buf, filename="topic_stats_pie.png"),
                ephemeral=True
            )

        except Exception as e:
            logging.error(f"Error in /topic_stats: {e}")
            try:
                await interaction.followup.send(
                    "❌ Error al obtener estadísticas del tópico.",
                    ephemeral=True
                )
            except Exception:
                pass