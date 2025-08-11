import logging
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import io
from discord import app_commands, Interaction, File
import discord

from repositories import stats_repository, quiz_repository
from repositories.server_repository import atualizar_ultima_interacao_servidor
from utils.utils import is_professor
from utils.structured_logging import structured_logger as logger

def register(tree: app_commands.CommandTree):
    
    @tree.command(name="stats", description="Shows a summary of the quizzes taken by all users (professors only)")
    async def estadisticas(interaction: discord.Interaction):
        # Log INMEDIATO antes de cualquier operación
        logger.info(f"🔍 Comando /stats ejecutado por {interaction.user.display_name}", 
                   command="stats",
                   user_id=str(interaction.user.id),
                   username=interaction.user.display_name,
                   guild_id=str(interaction.guild.id),
                   guild_name=interaction.guild.name,
                   channel_id=str(interaction.channel.id),
                   is_professor=is_professor(interaction),
                   operation="command_execution")
        
        try:
            atualizar_ultima_interacao_servidor(interaction.guild.id)

            if not is_professor(interaction):
                logger.warning("Access denied - non-professor attempted to use stats command",
                              command="stats",
                              user_id=str(interaction.user.id),
                              username=interaction.user.name,
                              guild_id=str(interaction.guild.id),
                              operation="access_denied")
                await interaction.response.send_message("\u26d4 This command is only available to professors.", ephemeral=True)
                return

            datos = stats_repository.obter_estatisticas_por_servidor(interaction.guild.id)

            if not datos:
                logger.info("No statistics available for guild",
                           command="stats",
                           user_id=str(interaction.user.id),
                           username=interaction.user.name,
                           guild_id=str(interaction.guild.id),
                           operation="no_stats_found")
                await interaction.response.send_message("📂 No statistics recorded yet.")
                return

            user_count = len(datos)
            total_attempts = sum(len(info['intentos']) for info in datos.values())
            
            resumen = "📊 **Bot usage statistics:**\n"
            for uid, info in datos.items():
                resumen += f"\n👤 {info['nombre']}: {len(info['intentos'])} attempt(s)"
                for intento in info['intentos'][-3:]:
                    resumen += f"\n  • {intento.get('topic_id', 'Unknown')}: {intento.get('success', 0)}/{intento.get('success', 0) + intento.get('failures', 0)}"

            logger.info("Stats command completed successfully",
                       command="stats",
                       user_id=str(interaction.user.id),
                       username=interaction.user.name,
                       guild_id=str(interaction.guild.id),
                       guild_name=interaction.guild.name,
                       channel_id=str(interaction.channel.id),
                       is_professor=is_professor(interaction),
                       operation="command_success",
                       user_count=user_count,
                       total_attempts=total_attempts)

            await interaction.response.send_message(resumen)
        except Exception as e:
            logger.error("Error in stats command",
                        command="stats",
                        user_id=str(interaction.user.id),
                        username=interaction.user.name,
                        guild_id=str(interaction.guild.id),
                        guild_name=interaction.guild.name,
                        channel_id=str(interaction.channel.id),
                        is_professor=is_professor(interaction),
                        operation="command_error",
                        error_type=type(e).__name__,
                        error_message=str(e))
            logging.error(f"Error retrieving statistics: {e}")
            
            # Verificar si ya respondimos a la interacción
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Error retrieving statistics.")
                else:
                    await interaction.followup.send("❌ Error retrieving statistics.", ephemeral=True)
            except Exception:
                logging.error("Failed to send error message to user")
            
    @tree.command(name="user_stats", description="Shows a summary of the quizzes taken by all users (professors only)")
    async def user_stats(interaction: discord.Interaction):
        logger.info("Command execution started", 
                   command="user_stats",
                   user_id=str(interaction.user.id),
                   username=interaction.user.name,
                   guild_id=str(interaction.guild.id),
                   guild_name=interaction.guild.name,
                   channel_id=str(interaction.channel.id),
                   is_professor=is_professor(interaction),
                   operation="command_execution")
        
        try:
            atualizar_ultima_interacao_servidor(interaction.guild.id)

            if not is_professor(interaction):
                logger.warning("Access denied - non-professor attempted to use user_stats command",
                              command="user_stats",
                              user_id=str(interaction.user.id),
                              username=interaction.user.name,
                              guild_id=str(interaction.guild.id),
                              operation="access_denied")
                await interaction.response.send_message("⛔ This command is only available to professors.", ephemeral=True)
                return

            dados = stats_repository.obter_estatisticas_por_servidor(interaction.guild.id)

            if not dados:
                logger.info("No statistics available for guild",
                           command="user_stats",
                           user_id=str(interaction.user.id),
                           username=interaction.user.name,
                           guild_id=str(interaction.guild.id),
                           operation="no_stats_found")
                await interaction.response.send_message("📂 No statistics recorded yet.")
                return

            nomes = []
            tentativas_por_usuario = {}

            for uid, info in dados.items():
                nome = info['nombre']
                intentos = info['intentos']
                tentativas = []

                for tentativa in intentos:
                    success = tentativa.get("success", 0)
                    failures = tentativa.get("failures", 0)
                    total = success + failures

                    if total == 0:
                        continue

                    media = success / total
                    tentativas.append(media)

                if tentativas:
                    nomes.append(nome)
                    tentativas_por_usuario[nome] = tentativas

            user_count = len(nomes)
            total_attempts = sum(len(tentativas) for tentativas in tentativas_por_usuario.values())

            fig, ax = plt.subplots(figsize=(12, 6))
            bottom_map = {nome: 0 for nome in nomes}

            for nome in nomes:
                tentativas = tentativas_por_usuario[nome]
                for media in tentativas:
                    cor = 'green' if media >= 0.5 else 'red'
                    ax.bar(nome, 1, bottom=bottom_map[nome], color=cor)
                    bottom_map[nome] += 1
                    
            max_tentativas = max(bottom_map.values(), default=0)
            limite_superior = ((max_tentativas + 4) // 5 + 1) * 5

            ax.set_title('Quiz attempts per user')
            ax.set_ylabel('Number of attempts')
            ax.set_yticks(range(0, limite_superior + 1, 5))
            ax.set_xlabel('Users')
            plt.xticks(rotation=45, ha='right')

            # Add legend
            legenda_verde = mpatches.Patch(color='green', label='≥ 50% correct')
            legenda_vermelha = mpatches.Patch(color='red', label='< 50% correct')
            ax.legend(handles=[legenda_verde, legenda_vermelha])

            # Export image
            buf = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plt.close(fig)

            logger.info("User stats command completed successfully",
                       command="user_stats",
                       user_id=str(interaction.user.id),
                       username=interaction.user.name,
                       guild_id=str(interaction.guild.id),
                       guild_name=interaction.guild.name,
                       channel_id=str(interaction.channel.id),
                       is_professor=is_professor(interaction),
                       operation="command_success",
                       user_count=user_count,
                       total_attempts=total_attempts)

            await interaction.response.send_message(
                content="📊 Quiz attempts per user (each bar segment = one attempt):",
                file=File(fp=buf, filename="user_stats_stacked.png")
            )

        except Exception as e:
            logger.error("Error in user_stats command",
                        command="user_stats",
                        user_id=str(interaction.user.id),
                        username=interaction.user.name,
                        guild_id=str(interaction.guild.id),
                        guild_name=interaction.guild.name,
                        channel_id=str(interaction.channel.id),
                        is_professor=is_professor(interaction),
                        operation="command_error",
                        error_type=type(e).__name__,
                        error_message=str(e))
            logging.error(f"Error generating user_stats graph: {e}")
            
            # Verificar si ya respondimos a la interacción
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Error retrieving statistics.")
                else:
                    await interaction.followup.send("❌ Error retrieving statistics.", ephemeral=True)
            except Exception:
                logging.error("Failed to send error message to user")
            
    @tree.command(name="time_stats", description="Shows a summary of the quizzes taken by all users (professors only)")
    async def time_stats(interaction: discord.Interaction):
        logger.info("Command execution started", 
                   command="time_stats",
                   user_id=str(interaction.user.id),
                   username=interaction.user.name,
                   guild_id=str(interaction.guild.id),
                   guild_name=interaction.guild.name,
                   channel_id=str(interaction.channel.id),
                   is_professor=is_professor(interaction),
                   operation="command_execution")
        
        try:
            atualizar_ultima_interacao_servidor(interaction.guild.id)

            if not is_professor(interaction):
                logger.warning("Access denied - non-professor attempted to use time_stats command",
                              command="time_stats",
                              user_id=str(interaction.user.id),
                              username=interaction.user.name,
                              guild_id=str(interaction.guild.id),
                              operation="access_denied")
                await interaction.response.send_message("\u26d4 This command is only available to professors.", ephemeral=True)
                return

            dados_temporais = quiz_repository.obter_quizzes_por_periodo(interaction.guild.id)

            if not dados_temporais:
                logger.info("No temporal statistics available for guild",
                           command="time_stats",
                           user_id=str(interaction.user.id),
                           username=interaction.user.name,
                           guild_id=str(interaction.guild.id),
                           operation="no_temporal_stats_found")
                await interaction.response.send_message("📂 No statistics recorded yet.")
                return

            datas = list(dados_temporais.keys())
            valores = list(dados_temporais.values())
            
            max_valor = max(valores, default=0)
            limite_superior = ((max_valor + 4) // 5 + 1) * 5

            fig, ax = plt.subplots()
            ax.plot(datas, valores, marker='o')
            ax.set_title('Quizzes over time')
            ax.set_xlabel('Date')
            ax.set_ylabel('Count')
            ax.set_yticks(range(0, limite_superior + 1, 5))
            plt.xticks(rotation=45)

            buf = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plt.close(fig)

            total_periods = len(datas)
            total_quizzes = sum(valores)

            logger.info("Time stats command completed successfully",
                       command="time_stats",
                       user_id=str(interaction.user.id),
                       username=interaction.user.name,
                       guild_id=str(interaction.guild.id),
                       guild_name=interaction.guild.name,
                       channel_id=str(interaction.channel.id),
                       is_professor=is_professor(interaction),
                       operation="command_success",
                       total_periods=total_periods,
                       total_quizzes=total_quizzes)

            await interaction.response.send_message("📈 Statistics over time:", file=discord.File(fp=buf, filename="time_stats.png"))

        except Exception as e:
            logger.error("Error in time_stats command",
                        command="time_stats",
                        user_id=str(interaction.user.id),
                        username=interaction.user.name,
                        guild_id=str(interaction.guild.id),
                        guild_name=interaction.guild.name,
                        channel_id=str(interaction.channel.id),
                        is_professor=is_professor(interaction),
                        operation="command_error",
                        error_type=type(e).__name__,
                        error_message=str(e))
            logging.error(f"Error retrieving time statistics: {e}")
            
            # Verificar si ya respondimos a la interacción
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ Error retrieving statistics. {e}")
                else:
                    await interaction.followup.send(f"❌ Error retrieving statistics. {e}", ephemeral=True)
            except Exception:
                logging.error("Failed to send error message to user")
