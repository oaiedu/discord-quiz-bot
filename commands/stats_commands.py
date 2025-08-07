import logging
import matplotlib.pyplot as plt
import io
from discord import app_commands, Interaction, File
import discord

from repositories import stats_repository, quiz_repository
from repositories.server_repository import atualizar_ultima_interacao_servidor
from utils.utils import is_professor

def register(tree: app_commands.CommandTree):
    
    @tree.command(name="stats", description="Muestra un resumen de los quizzes realizados por todos los usuarios (solo profesores)")
    async def estadisticas(interaction: discord.Interaction):
        atualizar_ultima_interacao_servidor(interaction.guild.id)

        if not is_professor(interaction):
            await interaction.response.send_message("\u26d4 Este comando solo está disponible para profesores.", ephemeral=True)
            return

        try:
            datos = stats_repository.obter_estatisticas_por_servidor(interaction.guild.id)

            if not datos:
                await interaction.response.send_message("📂 No hay estadísticas registradas todavía.")
                return

            resumen = "📊 **Estadísticas de uso del bot:**\n"
            for uid, info in datos.items():
                resumen += f"\n👤 {info['nombre']}: {len(info['intentos'])} intento(s)"
                for intento in info['intentos'][-3:]:
                    resumen += f"\n  • {intento.get('topic_id', 'Desconocido')}: {intento.get('success', 0)}/{intento.get('success', 0) + intento.get('failures', 0)}"

            await interaction.response.send_message(resumen)
        except Exception as e:
            logging.error(f"Erro ao obter estadísticas: {e}")
            await interaction.response.send_message("❌ Erro ao obter estadísticas.")
            
    @tree.command(name="user_stats", description="Muestra un resumen de los quizzes realizados por todos los usuarios (solo profesores)")
    async def user_stats(interaction: discord.Interaction):
        atualizar_ultima_interacao_servidor(interaction.guild.id)

        if not is_professor(interaction):
            await interaction.response.send_message("⛔ Este comando solo está disponible para profesores.", ephemeral=True)
            return

        try:
            dados = stats_repository.obter_estatisticas_por_servidor(interaction.guild.id)

            if not dados:
                await interaction.response.send_message("📂 No hay estadísticas registradas todavía.")
                return

            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
            import io
            from discord import File

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

            ax.set_title('Tentativas de quiz por usuário')
            ax.set_ylabel('Número de tentativas')
            ax.set_yticks([0, 5, 10, 15, 20, 25, 30])
            ax.set_xlabel('Usuários')
            plt.xticks(rotation=45, ha='right')

            # Adiciona legenda
            legenda_verde = mpatches.Patch(color='green', label='≥ 50% de acertos')
            legenda_vermelha = mpatches.Patch(color='red', label='< 50% de acertos')
            ax.legend(handles=[legenda_verde, legenda_vermelha])

            # Exporta imagem
            buf = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plt.close(fig)

            await interaction.response.send_message(
                content="📊 Tentativas de quiz por usuário (barra dividida por tentativa):",
                file=File(fp=buf, filename="user_stats_stacked.png")
            )

        except Exception as e:
            logging.error(f"Erro ao gerar gráfico de user_stats: {e}")
            await interaction.response.send_message("❌ Erro ao obter estadísticas.")
            
    @tree.command(name="time_stats", description="Muestra un resumen de los quizzes realizados por todos los usuarios (solo profesores)")
    async def time_stats(interaction: discord.Interaction):
        atualizar_ultima_interacao_servidor(interaction.guild.id)

        if not is_professor(interaction):
            await interaction.response.send_message("\u26d4 Este comando solo está disponible para profesores.", ephemeral=True)
            return

        try:
            dados_temporais = quiz_repository.obter_quizzes_por_periodo(interaction.guild.id)

            if not dados_temporais:
                await interaction.response.send_message("📂 No hay estadísticas registradas todavía.")
                return

            datas = list(dados_temporais.keys())
            valores = list(dados_temporais.values())

            fig, ax = plt.subplots()
            ax.plot(datas, valores, marker='o')
            ax.set_title('Quizzes realizados ao longo do tempo')
            ax.set_xlabel('Data')
            ax.set_ylabel('Quantidade')
            ax.set_yticks([0, 5, 10, 15, 20, 25, 30])
            plt.xticks(rotation=45)

            buf = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plt.close(fig)

            await interaction.response.send_message("📈 Estadísticas por período:", file=discord.File(fp=buf, filename="time_stats.png"))

        except Exception as e:
            logging.error(f"Erro ao obter estadísticas: {e}")
            await interaction.response.send_message(f"❌ Erro ao obter estadísticas. {e}")