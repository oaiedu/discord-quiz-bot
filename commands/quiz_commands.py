import logging
import random
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
from utils.utils import autocomplete_topics, register_user_statistics


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


def register(tree: app_commands.CommandTree):

    @tree.command(name="quiz", description="Take a quiz with 5 questions on a topic")
    @app_commands.describe(topic_name="Topic name")
    @app_commands.autocomplete(topic_name=autocomplete_topics)
    async def quiz(interaction: discord.Interaction, topic_name: str):
        # Immediate defer to avoid Discord 3-second timeout
        await interaction.response.defer(thinking=True, ephemeral=True)

        # Log command execution
        logger.info(f"🔍 Command /quiz executed by {interaction.user.display_name}",
                    command="quiz",
                    user_id=str(interaction.user.id),
                    username=interaction.user.display_name,
                    guild_id=str(
                        interaction.guild.id) if interaction.guild else None,
                    guild_name=interaction.guild.name if interaction.guild else None,
                    channel_id=str(
                        interaction.channel.id) if interaction.channel else None,
                    topic=topic_name,
                    operation="command_execution")

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

                correct = (
                    data.get('correct_answer', '') if q_type == 'Multiple Choice'
                    else ('T' if data.get('answer', 'T').upper().startswith('T') else 'F')
                )

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

            for i, (r, correct) in enumerate(user_answers):
                if r == correct:
                    result_text += f"✅ {i + 1}. Correct\n"
                    correct_count += 1
                else:
                    result_text += f"❌ {i + 1}. Incorrect (Correct answer: {correct})\n"

            result_text += f"\n🏁 You answered correctly {correct_count} out of {len(questions)} questions."
            await interaction.followup.send(result_text, ephemeral=True)

            question_types = set()
            for q in questions:
                q_type = q.to_dict().get('question_type', 'True/False')
                question_types.add(q_type)

            type_list = list(question_types)

            register_user_statistics(
                interaction.user, topic_name, correct_count, len(questions), type_list)
            save_statistic(interaction.guild.id, interaction.user,
                           topic_name, correct_count, len(questions))

            xp_gain = correct_count - (len(questions) - correct_count)
            final_xp = add_xp(str(interaction.user.id),
                              str(interaction.guild.id), xp_gain)
            await interaction.followup.send(
                f"✨ Você ganhou {xp_gain} XP! Seu total agora é {final_xp} XP.", ephemeral=True)

            streak = update_streak(str(interaction.user.id), str(
                interaction.guild.id), correct_count == len(questions))
            if streak >= 3:
                await interaction.followup.send(f"🔥 Você está em streak! ({streak} seguidas)", ephemeral=True)

            # Log command success
            logger.info(f"✅ Command /quiz successfully completed for {interaction.user.display_name}",
                        command="quiz",
                        user_id=str(interaction.user.id),
                        username=interaction.user.display_name,
                        guild_id=str(
                            interaction.guild.id) if interaction.guild else None,
                        topic=topic_name,
                        score=f"{correct_count}/{len(questions)}",
                        questions_count=len(questions),
                        operation="command_success")

        except Exception as e:
            logger.error(f"❌ Error in /quiz command: {e}",
                         command="quiz",
                         user_id=str(interaction.user.id),
                         username=interaction.user.display_name,
                         guild_id=str(
                             interaction.guild.id) if interaction.guild else None,
                         topic=topic_name,
                         error_type=type(e).__name__,
                         error_message=str(e),
                         operation="command_error")

            try:
                await interaction.followup.send("❌ An error occurred during the quiz.", ephemeral=True)
            except Exception:
                pass
            logging.error(f"Error during quiz: {e}")
            await interaction.response.send_message("❌ An error occurred during the quiz.", ephemeral=True)
