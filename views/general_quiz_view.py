import time
import discord
from discord import Interaction


class GeneralQuizRegistrationView(discord.ui.View):
    def __init__(self, session: dict, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.session = session
        self.message: discord.Message | None = None

    @discord.ui.button(label="Join quiz", style=discord.ButtonStyle.success)
    async def join_button(self, interaction: Interaction, button: discord.ui.Button):
        if not self.session.get("is_open", True):
            await interaction.response.send_message(
                "⏱️ Registration is closed.",
                ephemeral=True,
            )
            return

        user_id = interaction.user.id
        registered_users: set[int] = self.session.setdefault("users", set())
        if user_id in registered_users:
            await interaction.response.send_message(
                "✅ You are already registered.",
                ephemeral=True,
            )
            return

        registered_users.add(user_id)
        await interaction.response.send_message(
            "🎉 You are registered for the quiz.",
            ephemeral=True,
        )

    async def on_timeout(self):
        self.session["is_open"] = False
        for child in self.children:
            child.disabled = True

        if self.message:
            try:
                await self.message.edit(
                    content=(
                        "⏱️ Registration closed. The quiz will start shortly."
                    ),
                    view=None,
                )
            except Exception:
                pass


class GeneralQuizAnswerButton(discord.ui.Button):
    def __init__(self, label: str, correct_answer: str, parent_view: "GeneralQuizQuestionView"):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.correct_answer = correct_answer
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        user_id = interaction.user.id

        if user_id not in self.parent_view.allowed_users:
            await interaction.response.send_message(
                "⛔ You are not registered for this quiz.",
                ephemeral=True,
            )
            return

        if user_id in self.parent_view.answered_users:
            await interaction.response.send_message(
                "✅ You already answered this question.",
                ephemeral=True,
            )
            return

        self.parent_view.answered_users.add(user_id)
        is_correct = self.label.upper() == self.correct_answer.upper()
        elapsed = time.monotonic() - self.parent_view.question_start
        self.parent_view.record_answer(user_id, self.label.upper(), is_correct, elapsed)

        await interaction.response.send_message(
            "📝 Answer received.",
            ephemeral=True,
        )


class GeneralQuizQuestionView(discord.ui.View):
    def __init__(
        self,
        alternatives: dict[str, str],
        correct_answer: str,
        session: dict,
        question_id: str,
        allowed_users: set[int],
        timeout: int = 25,
    ):
        super().__init__(timeout=timeout)
        self.alternatives = alternatives
        self.correct_answer = correct_answer
        self.session = session
        self.question_id = question_id
        self.allowed_users = allowed_users
        self.answered_users: set[int] = set()
        self.message: discord.Message | None = None
        self.question_start = time.monotonic()

        for letter in alternatives:
            self.add_item(GeneralQuizAnswerButton(letter, correct_answer, self))

    def record_answer(self, user_id: int, choice: str, is_correct: bool, elapsed: float):
        answers = self.session.setdefault("answers", [])
        answers.append(
            {
                "question_id": self.question_id,
                "user_id": user_id,
                "choice": choice,
                "is_correct": is_correct,
                "elapsed": elapsed,
            }
        )

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass
