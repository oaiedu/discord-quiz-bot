import asyncio

import discord
from discord import Interaction
from discord.ui import Button, View


class ShortAnswerModal(discord.ui.Modal):
    def __init__(self, question_number: int, answer_future: asyncio.Future):
        super().__init__(title=f"Answer Q{question_number}")
        self.answer_future = answer_future
        self.answer_input = discord.ui.TextInput(
            label="Your answer",
            placeholder="Write a concise answer",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=500,
        )
        self.add_item(self.answer_input)

    async def on_submit(self, interaction: Interaction):
        answer_text = str(self.answer_input.value).strip()
        if not self.answer_future.done():
            self.answer_future.set_result(answer_text)
        await interaction.response.send_message("✅ Answer received.", ephemeral=True)


class ShortAnswerInputView(View):
    def __init__(self, owner_user_id: int, question_number: int, answer_future: asyncio.Future, timeout: float = 90):
        super().__init__(timeout=timeout)
        self.owner_user_id = owner_user_id
        self.question_number = question_number
        self.answer_future = answer_future

    @discord.ui.button(label="Answer", style=discord.ButtonStyle.primary)
    async def answer_button(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.owner_user_id:
            await interaction.response.send_message("This quiz isn't for you!", ephemeral=True)
            return

        if self.answer_future.done():
            await interaction.response.send_message("⚠️ This question was already answered.", ephemeral=True)
            return

        await interaction.response.send_modal(ShortAnswerModal(self.question_number, self.answer_future))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
