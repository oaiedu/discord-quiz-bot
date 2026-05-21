import logging
import random
import re
from discord import app_commands, Interaction, ButtonStyle
import discord
from discord.ui import View, Button
import asyncio
import math

from repositories.level_repository import add_xp, update_streak
from repositories.question_repository import update_question_stats
from repositories.server_repository import update_server_last_interaction
from repositories.stats_repository import save_statistic
from repositories.topic_repository import get_questions_by_topic
from utils.enum import QuestionType
from utils.structured_logging import structured_logger as logger
from utils.utils import autocomplete_quiz_topics, register_user_statistics, safe_defer, professor_verification
from views.general_quiz_view import QuizView, GeneralQuizJoinView, GeneralQuizQuestionView

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
                interaction.guild.id, topic_name)

            if not questions_data:
                await interaction.followup.send(
                    f"❌ There are no questions registered for the topic `{topic_name}`.",
                    ephemeral=True
                )
                logger.warning(f"❌ No questions found for topic: {topic_name}",
                               command="quiz",
                               user_id=str(interaction.user.id),
                               username=interaction.user.display_name,
                               guild_id=str(
                                   interaction.guild.id) if interaction.guild else None,
                               topic=topic_name,
                               operation="no_questions_found")
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

                alternatives = (
                    data.get('alternatives', {})
                    if q_type == QuestionType.MULTIPLE_CHOICE.value
                    else {'T': 'True', 'F': 'False'}
                )

                for letter, alt_text in alternatives.items():
                    text += f"\n{letter}. {alt_text}"

                if q_type == QuestionType.MULTIPLE_CHOICE.value:
                    correct = str(data.get('correct_answer', '')).strip().upper()
                else:
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

                async def answer_callback(interaction_inner, choice, correct, question_id=question_id, q=q):
                    if interaction.user.id != interaction_inner.user.id:
                        await interaction_inner.response.send_message("This quiz isn't for you!", ephemeral=True)
                        return False

                    is_correct = choice.upper() == correct.upper()
                    user_answers.append((choice.upper(), correct.upper()))

                    try:
                        update_question_stats(
                            guild_id=interaction.guild.id,
                            topic_id=q.reference.parent.parent.id,
                            question_id=question_id,
                            correct=is_correct
                        )
                    except Exception as err:
                        logger.warning(f"Error updating stats for question {question_id}: {err}",
                                       command="quiz",
                                       user_id=str(interaction.user.id),
                                       username=interaction.user.display_name,
                                       guild_id=str(
                                           interaction.guild.id) if interaction.guild else None,
                                       question_id=question_id,
                                       error_type=type(err).__name__,
                                       operation="stats_update_error")

                    return is_correct

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
            try:
                await interaction.followup.send("❌ An error occurred during the quiz.", ephemeral=True)
            except Exception:
                pass
            logging.error(f"Error during quiz: {e}")
            await interaction.response.send_message("❌ An error occurred during the quiz.", ephemeral=True)

            
    @tree.command(name="general_quiz", description="Start a general quiz for everyone")
    @app_commands.describe(topic_name="Topic name")
    @app_commands.autocomplete(topic_name=autocomplete_quiz_topics)
    async def general_quiz(interaction: discord.Interaction, topic_name: str):
        if not await safe_defer(interaction, thinking=True, ephemeral=False):
            return
        if not await professor_verification(interaction):
            return

        update_server_last_interaction(interaction.guild.id)

        questions_data = get_questions_by_topic(
            interaction.guild.id,
            topic_name,
            exclude_types=[QuestionType.SHORT_ANSWER.value],
        )
        if not questions_data:
            await interaction.followup.send(
                f"❌ No hay preguntas T/F o multiple choice para {topic_name}.",
                ephemeral=True
            )
            return

        questions = random.sample(questions_data, min(5, len(questions_data)))

        # 1) Join window (60s)
        join_view = GeneralQuizJoinView(timeout=None)
        join_msg = await interaction.followup.send(
            f"📣 ¡Arranca el quiz general de **{topic_name}**! Pulsa **Unirme** para entrar. Tienes **60s**.",
            view=join_view,
            wait=True
        )
        await asyncio.sleep(60)  # Wait for 60 seconds
        join_view.disable_all()
        await join_msg.edit(view=join_view)

        participants = join_view.participants  # set of user_ids
        if not participants:
            await interaction.followup.send("❌ Nadie se unio al quiz.")
            return

        participant_names = []
        for uid in participants:
            member = interaction.guild.get_member(uid)
            if member:
                participant_names.append(member.display_name)
            else:
                participant_names.append(str(uid))

        participants_text = "\n".join(participant_names) if participant_names else "Nadie"
        await interaction.followup.send(f"✅ Participantes confirmados:\n{participants_text}")

        # 2) Preguntas en loop
        user_scores = {uid: {"correct": 0, "total": 0, "points": 0} for uid in participants}

        valid_questions = 0

        for idx, q in enumerate(questions):
            data = q.to_dict()
            question_id = q.id
            topic_id = q.reference.parent.parent.id
            q_type = data.get("question_type", "True/False")

            raw_question = str(data.get("question", "")).strip()
            if not raw_question:
                continue

            if q_type == QuestionType.MULTIPLE_CHOICE.value:
                raw_alternatives = data.get("alternatives")
                if raw_alternatives in (None, "", {}):
                    raw_alternatives = data.get("options")

                alternatives = _normalize_multiple_choice_alternatives(raw_alternatives)
                if not alternatives:
                    logger.warning(
                        "Skipping malformed Multiple Choice question due to invalid alternatives/options.",
                        command="general_quiz",
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
                        command="general_quiz",
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
                        command="general_quiz",
                        user_id=str(interaction.user.id),
                        username=interaction.user.display_name,
                        guild_id=str(interaction.guild.id) if interaction.guild else None,
                        topic=topic_name,
                        question_id=question_id,
                        raw_answer=str(data.get("correct_answer", data.get("answer"))),
                        operation="invalid_true_false_answer"
                    )
                    continue

            question_text = f"**{idx + 1}. {raw_question}**"
            for letter, alt_text in alternatives.items():
                question_text += f"\n{letter}. {alt_text}"

            question_view = GeneralQuizQuestionView(
                alternatives=alternatives,
                correct_answer=correct,
                participants=participants,
                timeout=None,
            )

            msg = await interaction.followup.send(
                question_text,
                view=question_view
            )

            await asyncio.sleep(60)  # Wait for 60 seconds
            question_view.disable_all()
            await msg.edit(view=question_view)

            for uid, selected in question_view.answers.items():
                is_correct = selected == correct
                user_scores[uid]["total"] += 1
                if is_correct:
                    user_scores[uid]["correct"] += 1
                    answered_at = question_view.answer_times.get(uid, question_view.start_time)
                    elapsed = max(0.0, answered_at - question_view.start_time)
                    score = max(0, math.ceil(100 * (1 - elapsed / 60.0)))
                    user_scores[uid]["points"] += score

            if idx + 1 < len(questions):
                lines = [f"📊 Clasificacion provisional (pregunta {idx + 1}):"]

                sorted_scores = sorted(
                    user_scores.items(),
                    key=lambda item: (item[1].get("correct", 0), item[1].get("points", 0)),
                    reverse=True
                )

                for uid, stats in sorted_scores:
                    member = interaction.guild.get_member(uid)
                    name = member.display_name if member else str(uid)
                    lines.append(f"- {name}-- {stats['correct']} aciertos-- {stats['points']} puntos")

                await interaction.followup.send("\n".join(lines))

            valid_questions += 1

        if valid_questions == 0:
            await interaction.followup.send(
                "❌ No se encontraron preguntas validas para este quiz."
            )
            return
        
        # 3) Persistencia stats + XP por usuario
        for uid, stats in user_scores.items():
            member = interaction.guild.get_member(uid)
            if not member:
                continue
            register_user_statistics(
                member, topic_name, stats["correct"], stats["total"],
                [QuestionType.TRUE_FALSE.value, QuestionType.MULTIPLE_CHOICE.value]
            )
            save_statistic(interaction.guild.id, member, topic_name, stats["correct"], stats["total"])
            xp_gain = stats["correct"] - (stats["total"] - stats["correct"])
            add_xp(str(uid), str(interaction.guild.id), xp_gain)
            update_streak(str(uid), str(interaction.guild.id), stats["correct"] == stats["total"])
        
        lines = ["🏆 Clasificacion final"]

        sorted_scores = sorted(
            user_scores.items(),
            key=lambda item: (item[1].get("correct", 0), item[1].get("points", 0)),
            reverse=True
        )

        for uid, stats in sorted_scores:
            member = interaction.guild.get_member(uid)
            name = member.display_name if member else str(uid)
            lines.append(f"- {name}-- {stats['correct']} aciertos-- {stats['points']} puntos")

        await interaction.followup.send("\n".join(lines))

        await interaction.followup.send("✅ Fin del quiz. ¡Gracias por participar!")