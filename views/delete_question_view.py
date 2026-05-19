import discord
from discord import Interaction

from repositories.question_repository import delete_question


class DeleteQuestionModal(discord.ui.Modal, title="Delete Question"):
    def __init__(self, guild_id: int, topic: str, questions: list[dict]):
        super().__init__()
        self.guild_id = guild_id
        self.topic = topic
        self.questions = questions

        self.number_input = discord.ui.TextInput(
            label="Question number",
            placeholder=f"Enter a number between 1 and {len(questions)}",
            required=True,
            max_length=6,
        )
        self.add_item(self.number_input)

    async def on_submit(self, interaction: Interaction):
        try:
            # Acknowledge immediately to avoid "Unknown interaction" if DB work takes too long.
            await interaction.response.defer(ephemeral=True, thinking=False)

            user_input = str(self.number_input.value).strip()
            if not user_input.isdigit():
                await interaction.followup.send(
                    "❌ Invalid input. You must type numbers only.",
                    ephemeral=True,
                )
                return

            number = int(user_input)
            if number < 1 or number > len(self.questions):
                await interaction.followup.send(
                    f"❌ Invalid number `{number}`. It must be between 1 and {len(self.questions)}.",
                    ephemeral=True,
                )
                return

            question_to_delete = self.questions[number - 1]
            delete_question(self.guild_id, self.topic, question_to_delete["id"])
            await interaction.followup.send(
                f"🗑️ Question #{number} deleted from `{self.topic}`.",
                ephemeral=True,
            )

        except Exception as e:
            try:
                await interaction.followup.send(
                    f"❌ Failed to delete question: {e}",
                    ephemeral=True,
                )
            except Exception:
                pass


class DeleteQuestionView(discord.ui.View):
    def __init__(self, guild_id: int, topic: str, questions: list[dict], owner_user_id: int):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        self.topic = topic
        self.questions = questions
        self.owner_user_id = owner_user_id
        self._consumed = False

    @discord.ui.button(label="Enter question number", style=discord.ButtonStyle.danger)
    async def open_modal(self, interaction: Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_user_id:
            await interaction.response.send_message(
                "⚠️ Only the user who started this command can use this action.",
                ephemeral=True,
            )
            return

        if self._consumed:
            await interaction.response.send_message(
                "⚠️ This action was already used. Run `/delete_question` again if needed.",
                ephemeral=True,
            )
            return

        self._consumed = True

        # Remove the button from the original message so it cannot be reused.
        try:
            await interaction.message.edit(view=None)
        except Exception:
            pass

        await interaction.response.send_modal(
            DeleteQuestionModal(self.guild_id, self.topic, self.questions)
        )
