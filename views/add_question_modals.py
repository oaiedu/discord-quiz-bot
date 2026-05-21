import discord
from discord import Interaction
from discord.ui import Modal, TextInput

from repositories.question_repository import add_question
from utils.enum import QuestionType
from utils.utils import safe_defer, update_last_interaction


class AddQuestionBaseModal(Modal):
    def __init__(self, *, topic: str, question: str, question_type: QuestionType, title: str):
        super().__init__(title=title, timeout=180)
        self.topic = topic
        self.question = question
        self.question_type = question_type

    async def _save_question(
        self,
        interaction: Interaction,
        answer: str,
        alternatives: dict | None = None,
    ):
        deferred = False
        try:
            guild_id = interaction.guild.id if interaction.guild else interaction.guild_id
            if guild_id is None:
                await interaction.response.send_message(
                    "❌ This command can only be used in a server.",
                    ephemeral=True,
                )
                return

            # A modal submission must be acknowledged quickly to avoid Discord timeout.
            deferred = await safe_defer(interaction, thinking=False, ephemeral=True)
            if not deferred:
                return

            update_last_interaction(guild_id)
            new_id = add_question(
                guild_id,
                self.topic,
                self.question,
                answer,
                self.question_type,
                alternatives or {},
            )
            await interaction.followup.send(
                f"✅ {self.question_type.value} question added to {self.topic} with ID: {new_id}.",
                ephemeral=True,
            )
        except Exception as e:
            if deferred or interaction.response.is_done():
                await interaction.followup.send(f"❌ Failed to add question: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(
                    f"❌ Failed to add question: {e}",
                    ephemeral=True,
                )


class AddTrueFalseQuestionModal(AddQuestionBaseModal):
    correct_answer = TextInput(
        label="Correct answer (True/False)",
        placeholder="Write True or False",
        required=True,
        max_length=10,
    )

    def __init__(self, *, topic: str, question: str):
        super().__init__(
            topic=topic,
            question=question,
            question_type=QuestionType.TRUE_FALSE,
            title="Add True/False Question",
        )

    async def on_submit(self, interaction: Interaction):
        raw_answer = str(self.correct_answer.value).strip().upper()
        if raw_answer.startswith("T"):
            normalized_answer = "T"
        elif raw_answer.startswith("F"):
            normalized_answer = "F"
        else:
            await interaction.response.send_message(
                "❌ True/False answer must be True or False.",
                ephemeral=True,
            )
            return

        await self._save_question(interaction, normalized_answer)


class AddShortAnswerQuestionModal(AddQuestionBaseModal):
    correct_answer = TextInput(
        label="Correct answer",
        placeholder="Write the expected short answer",
        required=True,
        max_length=400,
        style=discord.TextStyle.paragraph,
    )

    def __init__(self, *, topic: str, question: str):
        super().__init__(
            topic=topic,
            question=question,
            question_type=QuestionType.SHORT_ANSWER,
            title="Add Short Answer Question",
        )

    async def on_submit(self, interaction: Interaction):
        normalized_answer = str(self.correct_answer.value).strip()
        if not normalized_answer:
            await interaction.response.send_message("❌ Answer cannot be empty.", ephemeral=True)
            return

        await self._save_question(interaction, normalized_answer)


class AddMultipleChoiceQuestionModal(AddQuestionBaseModal):
    option_a = TextInput(label="Option A", required=True, max_length=300)
    option_b = TextInput(label="Option B", required=True, max_length=300)
    option_c = TextInput(label="Option C", required=True, max_length=300)
    option_d = TextInput(label="Option D", required=True, max_length=300)
    correct_option = TextInput(
        label="Correct option (A/B/C/D)",
        placeholder="Example: B",
        required=True,
        max_length=4,
    )

    def __init__(self, *, topic: str, question: str):
        super().__init__(
            topic=topic,
            question=question,
            question_type=QuestionType.MULTIPLE_CHOICE,
            title="Add Multiple Choice Question",
        )

    async def on_submit(self, interaction: Interaction):
        alternatives = {
            "A": str(self.option_a.value).strip(),
            "B": str(self.option_b.value).strip(),
            "C": str(self.option_c.value).strip(),
            "D": str(self.option_d.value).strip(),
        }

        for letter, text in alternatives.items():
            if not text:
                await interaction.response.send_message(
                    f"❌ Option {letter} cannot be empty.",
                    ephemeral=True,
                )
                return

        answer_raw = str(self.correct_option.value).strip().upper()
        normalized_answer = answer_raw[:1] if answer_raw else ""
        if normalized_answer not in {"A", "B", "C", "D"}:
            await interaction.response.send_message(
                "❌ Correct option must be one of A/B/C/D.",
                ephemeral=True,
            )
            return

        await self._save_question(interaction, normalized_answer, alternatives)
