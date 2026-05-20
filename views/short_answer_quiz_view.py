import asyncio
import discord
from discord.ui import View, Button, Modal, TextInput


class ShortAnswerModal(Modal, title="Short Answer"):
    response_text = TextInput(
        label="Your answer",
        placeholder="Write a short answer...",
        required=True,
        max_length=400,
    )

    def __init__(self, owner_id: int, source_view: "ShortAnswerInputView"):
        super().__init__(timeout=90)
        self.owner_id = owner_id
        self.source_view = source_view

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ Only the quiz user can submit this answer.",
                ephemeral=True,
            )
            return

        answer = str(self.response_text.value).strip()
        if not answer:
            await interaction.response.send_message(
                "❌ Answer cannot be empty.",
                ephemeral=True,
            )
            return

        if not self.source_view.answer_future.done():
            self.source_view.answer_future.set_result(answer)

        for item in self.source_view.children:
            item.disabled = True
        self.source_view.stop()

        await interaction.response.send_message("✅ Answer submitted.", ephemeral=True)


class OpenShortAnswerModalButton(Button):
    def __init__(self, owner_id: int):
        super().__init__(label="Answer privately", style=discord.ButtonStyle.primary)
        self.owner_id = owner_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ Only the quiz user can answer this question.",
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(
            ShortAnswerModal(owner_id=self.owner_id, source_view=self.view)
        )


class ShortAnswerInputView(View):
    def __init__(self, owner_id: int, timeout: int = 90):
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        self.answer_future: asyncio.Future[str] = asyncio.get_event_loop().create_future()
        self.add_item(OpenShortAnswerModalButton(owner_id=owner_id))

    async def on_timeout(self):
        if not self.answer_future.done():
            self.answer_future.set_exception(asyncio.TimeoutError())

        for item in self.children:
            item.disabled = True
        self.stop()
