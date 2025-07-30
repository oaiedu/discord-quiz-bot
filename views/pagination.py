import settings
import discord
from discord.ext import commands
from commands.crud_questions import read_questions
import utils
import math

logger = settings.logging.getLogger("bot")

class PaginationView(discord.ui.View):
    def __init__(self, data: list, timeout=180):
        super().__init__(timeout=timeout)
        self.current_page = 1
        self.sep = 5
        self.data = data
        self.message = None  # será preenchido após o envio

    async def send(self, ctx):
        self.message = await ctx.send(view=self)
        await self.update_message(self.data[:self.sep])

    def create_embed(self, data):
        total_pages = max(1, (len(self.data) + self.sep - 1) // self.sep)
        embed = discord.Embed(title=f"Lista de Perguntas – Página {self.current_page} de {total_pages}")

        for item in data:
            pergunta = item.get("pregunta", "❓ Sem pergunta")
            resposta = item.get("respuesta", "❓")
            id_ = item.get("id", "N/A")

            embed.add_field(
                name=f"❓ {pergunta}",
                value=f"**Resposta:** {resposta} \n`ID: {id_}`",
                inline=False
            )

        return embed
    
    async def send_interaction(self, interaction: discord.Interaction):
        embed = self.create_embed(self.get_current_page_data())
        await interaction.response.send_message(embed=embed, view=self, ephemeral=True)
        self.message = await interaction.original_response()
    

    async def update_message(self,data):
        self.update_buttons()
        await self.message.edit(embed=self.create_embed(data), view=self)

    def update_buttons(self):
        total_pages = math.ceil(len(self.data) / self.sep)

        # Desabilita anterior se na primeira página
        if self.current_page == 1:
            self.children[0].disabled = True  # first_page_button
            self.children[1].disabled = True  # prev_button
        else:
            self.children[0].disabled = False
            self.children[1].disabled = False

        # Desabilita próximo se na última página
        if self.current_page >= total_pages:
            self.children[2].disabled = True  # next_button
            self.children[3].disabled = True  # last_page_button
        else:
            self.children[2].disabled = False
            self.children[3].disabled = False


    def get_current_page_data(self):
        from_item = (self.current_page - 1) * self.sep
        until_item = self.current_page * self.sep
        return self.data[from_item:until_item]



    @discord.ui.button(label="|<",
                       style=discord.ButtonStyle.green)
    async def first_page_button(self, interaction:discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page = 1

        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="<",
                       style=discord.ButtonStyle.primary)
    async def prev_button(self, interaction:discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page -= 1
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label=">",
                       style=discord.ButtonStyle.primary)
    async def next_button(self, interaction:discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page += 1
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label=">|",
                       style=discord.ButtonStyle.green)
    async def last_page_button(self, interaction:discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page = int(len(self.data) / self.sep) + 1
        await self.update_message(self.get_current_page_data())

def run():
    intents = discord.Intents.all()

    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        await utils.load_videocmds(bot)

    @bot.command()
    async def paginate(ctx, topic: str):
        data = read_questions()  # função que retorna o dicionário

        if topic not in data:
            await ctx.send(f"❌ Tópico `{topic}` não encontrado.")
            return

        perguntas = data[topic]  # lista de perguntas do tópico

        if not perguntas:
            await ctx.send(f"📭 Nenhuma pergunta encontrada em `{topic}`.")
            return

        pagination_view = PaginationView(timeout=None)
        pagination_view.data = perguntas
        await pagination_view.send(ctx)


    bot.run(settings.DISCORD_API_SECRET, root_logger=True)


if __name__ == "__main__":
    run()        