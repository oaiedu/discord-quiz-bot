import discord
from discord.ext import commands
import utils

class PaginationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)  # 3 minutos de timeout
        self.current_page = 1
        self.sep = 5  # Número de itens por página
        self.data = []
        
    async def send(self, ctx):
        self.message = await ctx.send(view=self)

    def create_embed(sel, data):
        embed = discord.Embed(title="Example")
        for item in data:
            embed.add_field(name=item, value=item, inline=False)
        return embed
    
    async def update_message(self, data):
        await self.message.edit(self.create_embed(data), view = self)

    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def nextButton(self, interaction:discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page += 1
        until_item = self.current_page * self.sep
        from_item = until_item - self.sep
        await self.update_message(self.data[from_item:until_item])

    @discord.ui.button(label="<", style=discord.ButtonStyle.primary)
    async def prevButton(self, interaction:discord.Interactions, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page -= 1
        until_item = self.current_page * self.sep
        from_item = until_item - self.sep
        await self.update_message(self.data[from_item:until_item])

    @discord.ui.button(label="!<", style=discord.ButtonStyle.primary)
    async def firstPageButton(self, interaction:discord.Interactions, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page = 1
        until_item = self.current_page * self.sep
        from_item = until_item - self.sep
        await self.update_message(self.data[:until_item])

    @discord.ui.button(label=">!", style=discord.ButtonStyle.primary)
    async def lastPageButton(self, interaction:discord.Interactions, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page = int(len(self.data) / self.sep) + 1
        until_item = self.current_page * self.sep
        from_item = until_item - self.sep
        await self.update_message(self.data[from_item:])
