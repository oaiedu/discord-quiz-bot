import logging
import random
import re
from discord import app_commands, Interaction, ButtonStyle
import discord
from discord.ui import View, Button

from repositories.level_repository import add_xp, update_streak
from repositories.question_repository import update_question_stats
from repositories.server_repository import update_server_last_interaction
from repositories.stats_repository import save_statistic
from repositories.topic_repository import get_questions_by_topic
from utils.enum import QuestionType
from utils.structured_logging import structured_logger as logger
from utils.utils import autocomplete_quiz_topics, register_user_statistics, safe_defer


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
            self.add_item(QuizButton(
                letter, correct_answer, on_click_callback, self))


def _normalize_true_false(value: str) -> str | None:
    if value is None:
        return None

    if isinstance(value, bool):
        return "T" if value else "F"

    normalized = str(value).strip().upper()
    if not normalized:
        return None

    # Accept values like "False.", "(True)", or "The answer is false".
    normalized = re.sub(r"[^A-Z]", "", normalized)

    if normalized in {"T", "TRUE", "V", "VERDADERO"}:
        return "T"
    if normalized in {"F", "FALSE", "FALSO"}:
        return "F"
    if "FALSE" in normalized or normalized.startswith("F"):
        return "F"
    if "TRUE" in normalized or normalized.startswith("T"):
        return "T"
    return None


def _extract_true_false_answer(data: dict) -> str | None:
    for key in ("correct_answer", "answer", "correctAnswer"):
        value = data.get(key)
        normalized = _normalize_true_false(value)
        if normalized:
            return normalized
    return None


def _normalize_multiple_choice_alternatives(raw):
    if isinstance(raw, dict):
        out = {}
        for k, v in raw.items():
            key = str(k).strip().upper()
            if key in {"A", "B", "C", "D"}:
                out[key] = str(v).strip()
        
        # Forzar orden visual y de botones: A, B, C, D
        return {k: out[k] for k in ("A", "B", "C", "D") if k in out}

    if isinstance(raw, list):
        letters = ["A", "B", "C", "D"]
        out = {}
        for i, v in enumerate(raw[:4]):
            out[letters[i]] = str(v).strip()
        return out

    return None

def _normalize_multiple_choice_answer(raw, alternatives: dict) -> str | None:
    if raw is None:
        return None

    s = str(raw).strip()
    if not s:
        return None

    upper = s.upper()

    # Casos: "A", "b", "C)", "D."
    m = re.match(r"^\s*([ABCD])\s*[\)\.\:\-]?\s*$", upper)
    if m:
        return m.group(1)

    # Casos: "answer: B", "option C", "respuesta D"
    m = re.search(r"\b(?:ANSWER|OPTION|RESPUESTA)?\s*[:\-]?\s*([ABCD])\b", upper)
    if m:
        return m.group(1)

    # Si viene el texto completo de la opción
    normalized_text = upper.strip()
    for letter, option_text in alternatives.items():
        if normalized_text == str(option_text).strip().upper():
            return letter

    return None


def register(tree: app_commands.CommandTree):

    @tree.command(name="quiz", description="Take a quiz with 5 questions on a topic")
    @app_commands.describe(topic_name="Topic name")
    @app_commands.autocomplete(topic_name=autocomplete_quiz_topics)
    async def quiz(interaction: discord.Interaction, topic_name: str):
        if not await safe_defer(interaction, thinking=True, ephemeral=True):
            return

        try:
            if interaction.guild:
                update_server_last_interaction(interaction.guild.id)

            questions_data = get_questions_by_topic(
                interaction.guild.id,
                topic_name,
            )

            if not questions_data:
                await interaction.followup.send(
                    f"❌ There are no True/False or Multiple Choice questions for {topic_name}. Use /short_answer_quiz for short-answer topics.",
                    ephemeral=True
                )
                return

            questions = random.sample(
                questions_data, min(5, len(questions_data)))

            await interaction.followup.send("📋 Starting the quiz...", ephemeral=True)

            user_answers = []

            for idx, q in enumerate(questions):
                data = q.to_dict()
                question_id = q.id
                q_type = data.get('question_type', 'True/False')
                text = f"**{idx + 1}. {data.get('question', '')}**"

                if q_type == QuestionType.MULTIPLE_CHOICE.value:
                    raw_alternatives = data.get("alternatives")
                    if raw_alternatives in (None, "", {}):
                        raw_alternatives = data.get("options")

                    alternatives = _normalize_multiple_choice_alternatives(raw_alternatives)
                    if not alternatives:
                        logger.warning(
                            "Skipping malformed Multiple Choice question due to invalid alternatives/options.",
                            command="quiz",
                            user_id=str(interaction.user.id),
                            username=interaction.user.display_name,
                            guild_id=str(interaction.guild.id) if interaction.guild else None,
                            topic=topic_name,
                            question_id=question_id,
                            operation="invalid_multiple_choice_alternatives"
                        )
                        continue

                    raw_correct = data.get("correct_answer", data.get("answer", ""))
                    correct = _normalize_multiple_choice_answer(raw_correct, alternatives)
                    if not correct or correct not in alternatives:
                        logger.warning(
                            "Skipping malformed Multiple Choice question due to invalid correct answer.",
                            command="quiz",
                            user_id=str(interaction.user.id),
                            username=interaction.user.display_name,
                            guild_id=str(interaction.guild.id) if interaction.guild else None,
                            topic=topic_name,
                            question_id=question_id,
                            raw_answer=str(raw_correct),
                            operation="invalid_multiple_choice_answer"
                        )
                        continue

                else:
                    alternatives = {"T": "True", "F": "False"}
                    correct = _extract_true_false_answer(data)
                    if not correct:
                        logger.warning(
                            "Skipping malformed True/False question due to invalid answer field.",
                            command="quiz",
                            user_id=str(interaction.user.id),
                            username=interaction.user.display_name,
                            guild_id=str(interaction.guild.id) if interaction.guild else None,
                            topic=topic_name,
                            question_id=question_id,
                            raw_answer=str(data.get("correct_answer", data.get("answer"))),
                            operation="invalid_true_false_answer"
                        )
                        continue

                topic_id = q.reference.parent.parent.id

                async def answer_callback(btn_interaction: discord.Interaction, selected: str, correct_answer: str):
                    is_correct = (selected == correct_answer)
                    user_answers.append((selected, correct_answer))

                    try:
                        update_question_stats(
                            btn_interaction.guild.id,
                            topic_id,
                            question_id,
                            is_correct
                        )
                    except Exception as stats_error:
                        logger.warning(
                            f"Failed to update question stats: {stats_error}",
                            command="quiz",
                            user_id=str(btn_interaction.user.id),
                            username=btn_interaction.user.display_name,
                            guild_id=str(btn_interaction.guild.id) if btn_interaction.guild else None,
                            topic=topic_name,
                            topic_id=topic_id,
                            question_id=question_id,
                            operation="update_question_stats_failed"
                        )

                    return is_correct

                for letter, alt_text in alternatives.items():
                    text += f"\n{letter}. {alt_text}"
                view = QuizView(alternatives, correct, answer_callback)
                await interaction.followup.send(text, view=view, ephemeral=True)

                timeout = await view.wait()
                if timeout:
                    await interaction.followup.send("⏰ Time's up for this question.", ephemeral=True)

                    logger.info(f"⏰ Quiz question timeout for {interaction.user.display_name}",
                                command="quiz",
                                user_id=str(interaction.user.id),
                                username=interaction.user.display_name,
                                guild_id=str(
                                    interaction.guild.id) if interaction.guild else None,
                                topic=topic_name,
                                question_number=idx + 1,
                                operation="question_timeout")
                    return
            result_text = "\n📊 Results:\n"
            correct_count = 0

            if not user_answers:
                await interaction.followup.send(
                    "❌ No valid questions were found for this quiz topic. Please review the stored answers.",
                    ephemeral=True,
                )
                return

            for i, (r, correct) in enumerate(user_answers):
                if r == correct:
                    result_text += f"✅ {i + 1}. Correct\n"
                    correct_count += 1
                else:
                    result_text += f"❌ {i + 1}. Incorrect (Correct answer: {correct})\n"

            result_text += f"\n🏁 You answered correctly {correct_count} out of {len(user_answers)} questions."
            await interaction.followup.send(result_text, ephemeral=True)

            question_types = set()
            for q in questions:
                q_type = q.to_dict().get('question_type', 'True/False')
                question_types.add(q_type)

            type_list = list(question_types)

            register_user_statistics(
                interaction.user, topic_name, correct_count, len(user_answers), type_list)
            save_statistic(interaction.guild.id, interaction.user,
                           topic_name, correct_count, len(user_answers))

            xp_gain = correct_count - (len(user_answers) - correct_count)
            final_xp = add_xp(str(interaction.user.id),
                              str(interaction.guild.id), xp_gain)
            await interaction.followup.send(
                f"✨ You gained {xp_gain} XP! Your total is now {final_xp} XP. Continue answering questions to earn more!", ephemeral=True)

            streak = update_streak(str(interaction.user.id), str(
                interaction.guild.id), correct_count == len(user_answers))
            if streak >= 3:
                await interaction.followup.send(f"🔥 You're on a streak! ({streak} in a row)", ephemeral=True)

        except Exception as e:
            logging.error(f"Error during quiz: {e}")
            try:
             await interaction.followup.send("❌ An error occurred during the quiz.", ephemeral=True)
            except Exception:
                pass