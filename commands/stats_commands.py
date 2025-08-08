import logging
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import io
from discord import app_commands, Interaction, File
import discord

from repositories import stats_repository, quiz_repository
from repositories.server_repository import atualizar_ultima_interacao_servidor
from utils.utils import is_professor

def register(tree: app_commands.CommandTree):
    
    @tree.command(name="stats", description="Shows a summary of the quizzes taken by all users (professors only)")
    async def estadisticas(interaction: discord.Interaction):
        atualizar_ultima_interacao_servidor(interaction.guild.id)

        if not is_professor(interaction):
            await interaction.response.send_message("\u26d4 This command is only available to professors.", ephemeral=True)
            return

        try:
            datos = stats_repository.obter_estatisticas_por_servidor(interaction.guild.id)

            if not datos:
                await interaction.response.send_message("📂 No statistics recorded yet.")
                return

            resumen = "📊 **Bot usage statistics:**\n"
            for uid, info in datos.items():
                resumen += f"\n👤 {info['nombre']}: {len(info['intentos'])} attempt(s)"
                for intento in info['intentos'][-3:]:
                    resumen += f"\n  • {intento.get('topic_id', 'Unknown')}: {intento.get('success', 0)}/{intento.get('success', 0) + intento.get('failures', 0)}"

            await interaction.response.send_message(resumen)
        except Exception as e:
            logging.error(f"Error retrieving statistics: {e}")
            await interaction.response.send_message("❌ Error retrieving statistics.")
            
    @tree.command(name="user_stats", description="Shows a summary of the quizzes taken by all users (professors only)")
    async def user_stats(interaction: discord.Interaction):
        atualizar_ultima_interacao_servidor(interaction.guild.id)

        if not is_professor(interaction):
            await interaction.response.send_message("⛔ This command is only available to professors.", ephemeral=True)
            return

        try:
            dados = stats_repository.obter_estatisticas_por_servidor(interaction.guild.id)

            if not dados:
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

            await interaction.response.send_message(
                content="📊 Quiz attempts per user (each bar segment = one attempt):",
                file=File(fp=buf, filename="user_stats_stacked.png")
            )

        except Exception as e:
            logging.error(f"Error generating user_stats graph: {e}")
            await interaction.response.send_message("❌ Error retrieving statistics.")
            
    @tree.command(name="time_stats", description="Shows a summary of the quizzes taken by all users (professors only)")
    async def time_stats(interaction: discord.Interaction):
        atualizar_ultima_interacao_servidor(interaction.guild.id)

        if not is_professor(interaction):
            await interaction.response.send_message("\u26d4 This command is only available to professors.", ephemeral=True)
            return

        try:
            dados_temporais = quiz_repository.obter_quizzes_por_periodo(interaction.guild.id)

            if not dados_temporais:
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

            await interaction.response.send_message("📈 Statistics over time:", file=discord.File(fp=buf, filename="time_stats.png"))

        except Exception as e:
            logging.error(f"Error retrieving time statistics: {e}")
            await interaction.response.send_message(f"❌ Error retrieving statistics. {e}")
