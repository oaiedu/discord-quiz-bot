import discord
from discord.ext import commands
import traceback
import utils

class PaginationView(discord.ui.View):
    def __init__(self, data, sep=5, ephemeral=False):
        super().__init__()
        self.data = data
        self.sep = sep
        self.current_page = 1
        self.ephemeral = ephemeral
        self.message = None

    current_page : int = 1
    sep : int = 1
    async def send(self, interaction: discord.Interaction):
        try:
            print("Enviando página inicial...")
            until_item = self.current_page * self.sep
            embed = self.create_embed(self.data[:until_item])
            await interaction.response.send_message(embed=embed, view=self, ephemeral=self.ephemeral)
            self.message = await interaction.original_response()
            print("Mensagem enviada com sucesso.")
        except Exception as e:
            print("Erro ao enviar mensagem inicial:")
            traceback.print_exc()

    def create_embed(self, data):
        embed = discord.Embed(title="Questions")
        for item in data:
            embed.add_field(name=str(item), value="\u200b", inline=False)
        return embed

    
    async def update_message(self, data):
        embed = self.create_embed(data)
        await self.message.edit(embed=embed, view=self)


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
