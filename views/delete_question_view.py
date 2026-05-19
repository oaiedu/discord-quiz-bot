import asyncio
import logging
import discord
from discord import Interaction
from discord.ui import View, Button, Modal, TextInput

from repositories.question_repository import delete_question

class DeleteQuestionView(View):
    def __init__(self, requester_id: int, guild_id: int, topic: str, questions: list):
        super().__init__(timeout=120)
        self.message = None
        self.used = False
        self.add_item(
            OpenDeleteQuestionModalButton(
                requester_id=requester_id,
                guild_id=guild_id,
                topic=topic,
                questions=questions
            )
        )

class OpenDeleteQuestionModalButton(Button):
    def __init__(self, requester_id: int, guild_id: int, topic: str, questions: list):
        super().__init__(
            label="Enter number privately",
            style=discord.ButtonStyle.danger
        )
        self.requester_id = requester_id
        self.guild_id = guild_id
        self.topic = topic
        self.questions = questions

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.requester_id:
            await interaction.response.send_message(
                "❌ Only the command author can use this button.",
                ephemeral=True
            )
            return

        if self.view.used:
            await interaction.response.send_message(
                "⚠️ This action was already used.",
                ephemeral=True
            )
            return

        self.view.used = True

        await interaction.response.send_modal(
            DeleteQuestionModal(
                guild_id=self.guild_id,
                topic=self.topic,
                questions=self.questions,
                source_view=self.view
            )
        )

class DeleteQuestionModal(Modal, title="Delete question"):
    question_number = TextInput(
        label="Question number",
        placeholder="Example: 3",
        required=True,
        max_length=5
    )

    def __init__(self, guild_id: int, topic: str, questions: list, source_view: View):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        self.topic = topic
        self.questions = questions
        self.source_view = source_view

    async def on_submit(self, interaction: Interaction):
        try:
            await interaction.response.defer(ephemeral=True, thinking=True)

            user_input = str(self.question_number.value).strip()
            if not user_input.isdigit():
                await interaction.followup.send("❌ Invalid input. You must send a number.", ephemeral=True)
                return

            selected_number = int(user_input)
            if selected_number < 1 or selected_number > len(self.questions):
                await interaction.followup.send(
                    f"❌ Invalid number. Choose between 1 and {len(self.questions)}.",
                    ephemeral=True
                )
                return

            selected_question = self.questions[selected_number - 1]
            selected_question_id = selected_question.get("id")
            if not selected_question_id:
                await interaction.followup.send("❌ Could not resolve question ID.", ephemeral=True)
                return

            await asyncio.to_thread(delete_question, self.guild_id, self.topic, selected_question_id)

            # Oculta el botón después del primer uso
            if self.source_view and getattr(self.source_view, "message", None):
                self.source_view.clear_items()
                self.source_view.stop()
                try:
                    await self.source_view.message.edit(
                        content="✅ Delete action already used.",
                        view=None
                    )
                except Exception:
                    pass

            selected_text = selected_question.get("question", "N/A")
            await interaction.followup.send(
                f"🗑️ Deleted question #{selected_number} from '{self.topic}': {selected_text}",
                ephemeral=True
            )

        except Exception as e:
            logging.error(f"Error deleting question from modal: {e}")
            await interaction.followup.send(f"❌ Failed to delete question: {e}", ephemeral=True)
