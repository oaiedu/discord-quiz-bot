import discord

class PaginationView(discord.ui.View):
    def __init__(self, data, ephemeral=False, per_page=5):
        super().__init__()
        self.data = data
        self.per_page = per_page
        self.current_page = 0
        self.ephemeral = ephemeral
        self.message = None  # Armazenará a mensagem para poder editá-la

    def format_page(self, page: int):
        start = page * self.per_page
        end = start + self.per_page
        items = self.data[start:end]

        embed = discord.Embed(title="Questions")
        for item in items:
            embed.add_field(name=item, value="\u200b", inline=False)
        embed.set_footer(text=f"Page {page + 1}/{(len(self.data) + self.per_page - 1) // self.per_page}")
        return embed

    async def send_message(self, content, view, ephemeral=False):
        try:
            self.message = await view.interaction.response.send_message(
                embed=self.format_page(0),
                view=self,
                ephemeral=self.ephemeral
            )
        except Exception as e:
            print(f"❌ Error sending paginated message: {e}")

    async def update_message(self):
        try:
            await self.message.edit(embed=self.format_page(self.current_page), view=self)
        except Exception as e:
            print(f"❌ Error updating message: {e}")

    def page_bounds(self):
        total_pages = (len(self.data) + self.per_page - 1) // self.per_page
        self.current_page = max(0, min(self.current_page, total_pages - 1))

    @discord.ui.button(label="<", style=discord.ButtonStyle.primary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page -= 1
        self.page_bounds()
        await self.update_message()

    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page += 1
        self.page_bounds()
        await self.update_message()

    @discord.ui.button(label="⏮️", style=discord.ButtonStyle.secondary)
    async def first(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page = 0
        await self.update_message()

    @discord.ui.button(label="⏭️", style=discord.ButtonStyle.secondary)
    async def last(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page = (len(self.data) - 1) // self.per_page
        await self.update_message()
