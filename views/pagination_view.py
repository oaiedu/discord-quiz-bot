from discord import Interaction, app_commands
from discord.ext import commands
import discord

# Classe para lidar com a visualização paginada
class PaginationView(discord.ui.View):
    def __init__(self, interaction: Interaction, data, topic, per_page=10):
        super().__init__(timeout=180)  # 3 min timeout
        self.interaction = interaction
        self.data = data
        self.topic = topic
        self.per_page = per_page
        self.current_page = 0
        self.total_pages = (len(data) - 1) // per_page + 1

    def format_page(self, page_index):
        start = page_index * self.per_page
        end = start + self.per_page
        preguntas = self.data[start:end]
        mensaje = f"📚 Questions for `{self.topic}` (Page {page_index + 1}/{self.total_pages}):\n\n"
        for i, q in enumerate(preguntas, start=start + 1):
            mensaje += f"{i}. {q['pregunta']} (Answer: {q['respuesta']}, ID: `{q['id']}`)\n"
        return mensaje

    async def update_message(self, interaction: Interaction):
        content = self.format_page(self.current_page)
        await interaction.response.edit_message(content=content, view=self)

    @discord.ui.button(label="⏪ Previous", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_message(interaction)
        else:
            await interaction.response.defer()  # Nada acontece se já estiver na primeira página

    @discord.ui.button(label="Next ⏩", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            await self.update_message(interaction)
        else:
            await interaction.response.defer()
