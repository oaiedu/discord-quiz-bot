import logging
import random
import re
from discord import app_commands, Interaction, ButtonStyle
import discord
from discord.ui import View, Button
import asyncio

from repositories.level_repository import add_xp, update_streak
from repositories.question_repository import update_question_stats
from repositories.server_repository import update_server_last_interaction
from repositories.stats_repository import save_statistic
from repositories.topic_repository import get_questions_by_topic
from utils.enum import QuestionType
from utils.structured_logging import structured_logger as logger
from utils.utils import autocomplete_quiz_topics, register_user_statistics, safe_defer
from utils.llm_utils import grade_short_answers
from views.short_answer_view import ShortAnswerInputView, ShortAnswerModal


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

def _extract_short_answer_text(data: dict) -> str | None:
        for key in ("correct_answer", "answer", "correctAnswer"):
            value = data.get(key)
            if value is None:
                continue
            normalized = str(value).strip()
            if normalized:
                return normalized
        return None
    
def _safe_float(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


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

    @tree.command(name="short_answer_quiz", description="Take a short-answer quiz with 5 questions on a topic")
    @app_commands.describe(topic_name="Topic name")
    @app_commands.autocomplete(topic_name=autocomplete_quiz_topics)
    async def short_answer_quiz(interaction: discord.Interaction, topic_name: str):
        if not await safe_defer(interaction, thinking=True, ephemeral=True):
            return

        try:
            if interaction.guild:
                update_server_last_interaction(interaction.guild.id)

            question_docs = get_questions_by_topic(interaction.guild.id, topic_name)
            if not question_docs:
                await interaction.followup.send(
                    f"❌ There are no questions registered for the topic `{topic_name}`.",
                    ephemeral=True,
                )
                return

            short_answer_docs = []
            for doc in question_docs:
                data = doc.to_dict() or {}
                if data.get("question_type") == QuestionType.SHORT_ANSWER.value:
                    short_answer_docs.append(doc)

            if len(short_answer_docs) < 5:
                await interaction.followup.send(
                    f"❌ Topic `{topic_name}` needs at least 5 Short Answer questions (found {len(short_answer_docs)}).",
                    ephemeral=True,
                )
                return

            selected_questions = random.sample(short_answer_docs, 5)
            await interaction.followup.send("🧠 Starting short-answer quiz (5 questions)...", ephemeral=True)

            collected_answers = []

            for idx, question_doc in enumerate(selected_questions, start=1):
                data = question_doc.to_dict() or {}
                question_text = str(data.get("question", "")).strip()
                expected_answer = _extract_short_answer_text(data)

                if not question_text or not expected_answer:
                    continue

                answer_future = asyncio.get_running_loop().create_future()
                input_view = ShortAnswerInputView(interaction.user.id, idx, answer_future, timeout=90)

                question_message = await interaction.followup.send(
                    f"**{idx}. {question_text}**\nClick **Answer** and submit your response.",
                    ephemeral=True,
                    view=input_view,
                    wait=True,
                )

                try:
                    user_answer = await asyncio.wait_for(answer_future, timeout=95)
                except asyncio.TimeoutError:
                    for child in input_view.children:
                        child.disabled = True
                    try:
                        await question_message.edit(view=input_view)
                    except Exception:
                        pass

                    await interaction.followup.send("⏰ Time's up for this question.", ephemeral=True)
                    return
                finally:
                    input_view.stop()
                    for child in input_view.children:
                        child.disabled = True
                    try:
                        await question_message.edit(view=input_view)
                    except Exception:
                        pass

                collected_answers.append({
                    "question_index": idx,
                    "topic_id": question_doc.reference.parent.parent.id,
                    "question_id": question_doc.id,
                    "question": question_text,
                    "expected_answer": expected_answer,
                    "user_answer": str(user_answer).strip(),
                })

            if len(collected_answers) != 5:
                await interaction.followup.send(
                    "❌ Could not collect all 5 valid short-answer questions. Please review stored data.",
                    ephemeral=True,
                )
                return

            await interaction.followup.send(
                "🤖 AI validating your answers...",
                ephemeral=True,
            )

            grading = await grade_short_answers(topic_name, collected_answers)
            if not grading:
                await interaction.followup.send(
                    "⚠️ Could not grade your short answers right now (OpenRouter failed). Please try again.",
                    ephemeral=True,
                )
                return

            score = max(0.0, min(10.0, float(grading.get("score", 0.0))))
            xp_gain = int(round(score / 2))
            summary = grading.get("summary", "")
            per_question = grading.get("per_question", [])

            per_question_by_index = {}
            for item in per_question:
                idx = int(_safe_float(item.get("question_index"), 0))
                if idx > 0:
                    per_question_by_index[idx] = item

            feedback_lines = [f"📊 Final grade: **{score:.1f}/10**"]
            if summary:
                feedback_lines.append(f"📝 {summary}")

            normalized_correct_count = 0
            for item in collected_answers:
                idx = item["question_index"]
                eval_item = per_question_by_index.get(idx, {})
                item_score = max(0.0, min(2.0, _safe_float(eval_item.get("score"), 0.0)))
                comment = str(eval_item.get("comment", "")).strip()

                if item_score >= 1.0:
                    normalized_correct_count += 1

                if comment:
                    feedback_lines.append(f"{idx}. {item_score:.1f}/2 - {comment}")
                else:
                    feedback_lines.append(f"{idx}. {item_score:.1f}/2")

                try:
                    update_question_stats(
                        guild_id=interaction.guild.id,
                        topic_id=item["topic_id"],
                        question_id=item["question_id"],
                        correct=item_score >= 1.0,
                    )
                except Exception as err:
                    logger.warning(
                        f"Error updating short-answer stats for question {item['question_id']}: {err}",
                        command="short_answer_quiz",
                        user_id=str(interaction.user.id),
                        username=interaction.user.display_name,
                        guild_id=str(interaction.guild.id) if interaction.guild else None,
                        question_id=item["question_id"],
                        error_type=type(err).__name__,
                        operation="stats_update_error",
                    )

            await interaction.followup.send("\n".join(feedback_lines), ephemeral=True)

            register_user_statistics(
                interaction.user,
                topic_name,
                normalized_correct_count,
                len(collected_answers),
                [QuestionType.SHORT_ANSWER.value],
            )
            save_statistic(
                interaction.guild.id,
                interaction.user,
                topic_name,
                normalized_correct_count,
                len(collected_answers),
            )

            final_xp = add_xp(str(interaction.user.id), str(interaction.guild.id), xp_gain)
            await interaction.followup.send(
                f"✨ You gained {xp_gain} XP. Your total is now {final_xp} XP.",
                ephemeral=True,
            )

            streak = update_streak(
                str(interaction.user.id),
                str(interaction.guild.id),
                score >= 8.0,
            )
            if streak >= 3:
                await interaction.followup.send(f"🔥 You're on a streak! ({streak} in a row)", ephemeral=True)

        except asyncio.TimeoutError:
            try:
                await interaction.followup.send(
                    "⏱️ Grading took too long. Please try again in a moment.",
                    ephemeral=True,
                )
            except Exception:
                pass
        except Exception as e:
            try:
                await interaction.followup.send("❌ An error occurred during short_answer_quiz.", ephemeral=True)
            except Exception:
                pass
            logging.error(f"Error during short_answer_quiz: {e}")