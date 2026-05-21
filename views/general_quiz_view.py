import asyncio

import discord
from discord import ButtonStyle
from discord.ui import View, Button


class QuizButton(Button):
    def __init__(self, label: str, correct_answer: str, on_click_callback, parent_view: View):
        super().__init__(label=label, style=ButtonStyle.primary)
        self.correct_answer = correct_answer
        self.on_click_callback = on_click_callback
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        is_correct = await self.on_click_callback(interaction, self.label, self.correct_answer)

        for item in self.parent_view.children:
            item.disabled = True

        if is_correct:
            self.style = ButtonStyle.success
        else:
            self.style = ButtonStyle.danger

        await interaction.response.edit_message(view=self.parent_view)

        self.parent_view.stop()


class QuizView(View):
    def __init__(self, alternatives, correct_answer, on_click_callback, timeout=60):
        super().__init__(timeout=timeout)
        for letter in alternatives:
            self.add_item(QuizButton(letter, correct_answer, on_click_callback, self))


class GeneralQuizJoinButton(Button):
    def __init__(self, parent_view: "GeneralQuizJoinView"):
        super().__init__(label="Unirme al quiz", style=ButtonStyle.primary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        if user_id in self.parent_view.participants:
            await interaction.response.send_message(
                "⚠ Ya estas unido al quiz.",
                ephemeral=True,
            )
            return

        self.parent_view.participants.add(user_id)
        await interaction.response.send_message(
            "✅ Te has unido al quiz.",
            ephemeral=True,
        )


class GeneralQuizJoinView(View):
    def __init__(self, timeout=60):
        super().__init__(timeout=timeout)
        self.participants: set[int] = set()
        self.add_item(GeneralQuizJoinButton(self))

    def disable_all(self):
        for item in self.children:
            item.disabled = True


class GeneralQuizQuestionButton(Button):
    def __init__(self, label: str, parent_view: "GeneralQuizQuestionView"):
        super().__init__(label=label, style=ButtonStyle.primary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        if user_id not in self.parent_view.participants:
            await interaction.response.send_message(
                "❌ No estas unido al quiz.",
                ephemeral=True,
            )
            return

        if user_id in self.parent_view.answers:
            await interaction.response.send_message(
                "⚠ Ya respondiste esta pregunta.",
                ephemeral=True,
            )
            return

        self.parent_view.answers[user_id] = self.label
        self.parent_view.answer_times[user_id] = asyncio.get_event_loop().time()
        await interaction.response.send_message(
            "✅ Respuesta registrada.",
            ephemeral=True,
        )


class GeneralQuizQuestionView(View):
    def __init__(self, alternatives, correct_answer, participants, timeout=60):
        super().__init__(timeout=timeout)
        self.participants = set(participants)
        self.correct_answer = correct_answer
        self.answers: dict[int, str] = {}
        self.answer_times: dict[int, float] = {}
        self.start_time = asyncio.get_event_loop().time()

        for letter in alternatives:
            self.add_item(GeneralQuizQuestionButton(letter, self))

    def disable_all(self):
        for item in self.children:
            item.disabled = True