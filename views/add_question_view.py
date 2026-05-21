import discord
from discord import Interaction
from typing import Awaitable, Callable

from utils.enum import QuestionType


SaveQuestionCallback = Callable[[Interaction, dict], Awaitable[None]]


class AddTrueFalseQuestionModal(discord.ui.Modal):
    def __init__(
        self,
        topic: str,
        question_text: str,
        on_save: SaveQuestionCallback,
    ):
        super().__init__(title="Add True/False Question")
        self.topic = topic
        self.question_text = question_text
        self.on_save = on_save

        self.answer_input = discord.ui.TextInput(
            label="Correct answer",
            placeholder="T or F",
            required=True,
            max_length=1,
        )
        self.add_item(self.answer_input)

    async def on_submit(self, interaction: Interaction):
        answer = str(self.answer_input.value).strip().upper()
        if answer not in ("T", "F"):
            await interaction.response.send_message(
                "❌ Invalid answer. Use T or F.",
                ephemeral=True,
            )
            return

        payload = {
            "question": self.question_text,
            "question_type": QuestionType.TRUE_FALSE.value,
            "correct_answer": answer,
        }
        await self.on_save(interaction, payload)


class AddMultipleChoiceQuestionModal(discord.ui.Modal):
    def __init__(
        self,
        topic: str,
        question_text: str,
        on_save: SaveQuestionCallback,
    ):
        super().__init__(title="Add Multiple Choice Question")
        self.topic = topic
        self.question_text = question_text
        self.on_save = on_save

        self.option_a = discord.ui.TextInput(label="Option A", required=True, max_length=200)
        self.option_b = discord.ui.TextInput(label="Option B", required=True, max_length=200)
        self.option_c = discord.ui.TextInput(label="Option C", required=True, max_length=200)
        self.option_d = discord.ui.TextInput(label="Option D", required=True, max_length=200)
        self.correct_letter = discord.ui.TextInput(
            label="Correct option",
            placeholder="A, B, C or D",
            required=True,
            max_length=1,
        )

        self.add_item(self.option_a)
        self.add_item(self.option_b)
        self.add_item(self.option_c)
        self.add_item(self.option_d)
        self.add_item(self.correct_letter)

    async def on_submit(self, interaction: Interaction):
        correct = str(self.correct_letter.value).strip().upper()
        if correct not in ("A", "B", "C", "D"):
            await interaction.response.send_message(
                "❌ Invalid correct option. Use A, B, C or D.",
                ephemeral=True,
            )
            return

        alternatives = {
            "A": str(self.option_a.value).strip(),
            "B": str(self.option_b.value).strip(),
            "C": str(self.option_c.value).strip(),
            "D": str(self.option_d.value).strip(),
        }

        if len(set(alternatives.values())) < 4:
            await interaction.response.send_message(
                "❌ Options must be different from each other.",
                ephemeral=True,
            )
            return

        payload = {
            "question": self.question_text,
            "question_type": QuestionType.MULTIPLE_CHOICE.value,
            "correct_answer": correct,
            "alternatives": alternatives,
        }
        await self.on_save(interaction, payload)


class AddShortAnswerQuestionModal(discord.ui.Modal):
    def __init__(
        self,
        topic: str,
        question_text: str,
        on_save: SaveQuestionCallback,
    ):
        super().__init__(title="Add Short Answer Question")
        self.topic = topic
        self.question_text = question_text
        self.on_save = on_save

        self.answer_input = discord.ui.TextInput(
            label="Expected answer",
            placeholder="Write the expected short answer",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=500,
        )
        self.add_item(self.answer_input)

    async def on_submit(self, interaction: Interaction):
        answer = str(self.answer_input.value).strip()
        if not answer:
            await interaction.response.send_message(
                "❌ Answer cannot be empty.",
                ephemeral=True,
            )
            return

        payload = {
            "question": self.question_text,
            "question_type": QuestionType.SHORT_ANSWER.value,
            "correct_answer": answer,
        }
        await self.on_save(interaction, payload)