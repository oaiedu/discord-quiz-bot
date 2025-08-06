import logging
from discord import app_commands, Interaction
import discord

from repositories import stats_repository
from repositories.server_repository import atualizar_ultima_interacao_servidor
from utils.utils import is_professor

def register(tree: app_commands.CommandTree):
    
    @tree.command(name="stats", description="Muestra un resumen de los quizzes realizados por todos los usuarios (solo profesores)")
    async def estadisticas(interaction: discord.Interaction):
        atualizar_ultima_interacao_servidor(interaction.guild.id)

        if not is_professor:
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