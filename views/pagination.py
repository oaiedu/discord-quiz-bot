# import settings
# import discord
# from discord.ext import commands
# import utils

# logger = settings.logging.getLogger("bot")

# class PaginationView(discord.ui.View):
#     current_page : int = 1
#     sep : int = 5

#     async def send(self, ctx):
#         self.message = await ctx.send(view=self)
#         await self.update_message(self.data[:self.sep])

#     def create_embed(self, data):
#         total_pages = max(1, (len(self.data) + self.sep - 1) // self.sep)
#         embed = discord.Embed(title=f"Lista de Perguntas – Página {self.current_page} de {total_pages}")

#         for item in data:
#             pergunta = item.get("pregunta", "❓ Sem pergunta")
#             resposta = item.get("respuesta", "❓")
#             id_ = item.get("id", "N/A")

#             embed.add_field(
#                 name=f"❓ {pergunta}",
#                 value=f"**Resposta:** {resposta} \n`ID: {id_}`",
#                 inline=False
#             )

#         return embed

#     async def update_message(self,data):
#         self.update_buttons()
#         await self.message.edit(embed=self.create_embed(data), view=self)

#     def update_buttons(self):
#         if self.current_page == 1:
#             self.first_page_button.disabled = True
#             self.prev_button.disabled = True
#             self.first_page_button.style = discord.ButtonStyle.gray
#             self.prev_button.style = discord.ButtonStyle.gray
#         else:
#             self.first_page_button.disabled = False
#             self.prev_button.disabled = False
#             self.first_page_button.style = discord.ButtonStyle.green
#             self.prev_button.style = discord.ButtonStyle.primary

#         if self.current_page == int(len(self.data) / self.sep) + 1:
#             self.next_button.disabled = True
#             self.last_page_button.disabled = True
#             self.last_page_button.style = discord.ButtonStyle.gray
#             self.next_button.style = discord.ButtonStyle.gray
#         else:
#             self.next_button.disabled = False
#             self.last_page_button.disabled = False
#             self.last_page_button.style = discord.ButtonStyle.green
#             self.next_button.style = discord.ButtonStyle.primary

#     def get_current_page_data(self):
#         until_item = self.current_page * self.sep
#         from_item = until_item - self.sep
#         if not self.current_page == 1:
#             from_item = 0
#             until_item = self.sep
#         if self.current_page == int(len(self.data) / self.sep) + 1:
#             from_item = self.current_page * self.sep - self.sep
#             until_item = len(self.data)
#         return self.data[from_item:until_item]


#     @discord.ui.button(label="|<",
#                        style=discord.ButtonStyle.green)
#     async def first_page_button(self, interaction:discord.Interaction, button: discord.ui.Button):
#         await interaction.response.defer()
#         self.current_page = 1

#         await self.update_message(self.get_current_page_data())

#     @discord.ui.button(label="<",
#                        style=discord.ButtonStyle.primary)
#     async def prev_button(self, interaction:discord.Interaction, button: discord.ui.Button):
#         await interaction.response.defer()
#         self.current_page -= 1
#         await self.update_message(self.get_current_page_data())

#     @discord.ui.button(label=">",
#                        style=discord.ButtonStyle.primary)
#     async def next_button(self, interaction:discord.Interaction, button: discord.ui.Button):
#         await interaction.response.defer()
#         self.current_page += 1
#         await self.update_message(self.get_current_page_data())

#     @discord.ui.button(label=">|",
#                        style=discord.ButtonStyle.green)
#     async def last_page_button(self, interaction:discord.Interaction, button: discord.ui.Button):
#         await interaction.response.defer()
#         self.current_page = int(len(self.data) / self.sep) + 1
#         await self.update_message(self.get_current_page_data())
