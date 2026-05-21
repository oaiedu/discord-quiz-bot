import logging
from discord import app_commands, Interaction

from repositories.question_repository import (list_questions_by_topic, add_question, delete_question, delete_all_questions_by_topic)
from repositories.topic_repository import get_topic_by_name
from utils.enum import QuestionType
from utils.llm_utils import generate_questions_from_pdf
from utils.structured_logging import structured_logger as logger
from utils.utils import professor_verification, update_last_interaction, autocomplete_question_type, is_professor, autocomplete_topics, autocomplete_all_topics, autocomplete_TF, safe_defer
from views.add_question_modals import AddTrueFalseQuestionModal, AddShortAnswerQuestionModal, AddMultipleChoiceQuestionModal


def _resolve_question_type(raw_type: str) -> QuestionType | None:
    try:
        return QuestionType(raw_type)
    except ValueError:
        normalized_type = str(raw_type).strip().upper().replace(" ", "_")
        if normalized_type in QuestionType.__members__:
            return QuestionType[normalized_type]
        return None

# Register commands

def register(tree: app_commands.CommandTree):
    
    @tree.command(name="add_question", description="Add a question to a topic (Professors only)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        topic="Topic name",
        question="Question text",
        type="Question type",
    )
    @app_commands.autocomplete(topic=autocomplete_all_topics, type=autocomplete_question_type)
    async def add_question_command(
        interaction: Interaction,
        topic: str,
        question: str,
        type: str,
    ):
        if not await professor_verification(interaction):
            return

        try:
            guild_id = interaction.guild.id if interaction.guild else interaction.guild_id
            if guild_id is None:
                await interaction.response.send_message(
                    "❌ This command can only be used in a server.",
                    ephemeral=True,
                )
                return

            update_last_interaction(guild_id)

            if not str(question).strip():
                await interaction.response.send_message("❌ Question cannot be empty.", ephemeral=True)
                return

            topic_data = get_topic_by_name(guild_id, topic)
            if not topic_data:
                await interaction.response.send_message(
                    f"❌ Topic '{topic}' does not exist.",
                    ephemeral=True,
                )
                return

            question_type = _resolve_question_type(type)
            if not question_type:
                await interaction.response.send_message(
                    f"❌ Invalid question type: {type}",
                    ephemeral=True,
                )
                return

            if question_type == QuestionType.TRUE_FALSE:
                await interaction.response.send_modal(
                    AddTrueFalseQuestionModal(topic=topic, question=question)
                )
            elif question_type == QuestionType.SHORT_ANSWER:
                await interaction.response.send_modal(
                    AddShortAnswerQuestionModal(topic=topic, question=question)
                )
            elif question_type == QuestionType.MULTIPLE_CHOICE:
                await interaction.response.send_modal(
                    AddMultipleChoiceQuestionModal(topic=topic, question=question)
                )
            else:
                await interaction.response.send_message(
                    f"❌ Unsupported question type: {question_type.value}",
                    ephemeral=True,
                )

        except Exception as e:
            if interaction.response.is_done():
                try:
                    await interaction.followup.send(f"❌ Failed to start add question flow: {e}", ephemeral=True)
                except Exception:
                    pass
            else:
                await interaction.response.send_message(
                    f"❌ Failed to start add question flow: {e}",
                    ephemeral=True,
                )

    @tree.command(name="list_questions", description="List questions for a topic (Professors only)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(topic="Topic name")
    @app_commands.autocomplete(topic=autocomplete_topics)
    async def list_questions_command(interaction: Interaction, topic: str):
        if not await professor_verification(interaction):
            return
        if not await safe_defer(interaction, thinking=True, ephemeral=True):
            return

        try:
            update_last_interaction(interaction.guild.id)

            questions = list_questions_by_topic(interaction.guild.id, topic)

            if not questions:
                await interaction.followup.send(f"📭 No questions found for `{topic}`.", ephemeral=True)
                logger.info(f"📭 No questions found for topic: {topic}",
                            command="list_questions",
                            user_id=str(interaction.user.id),
                            username=interaction.user.display_name,
                            guild_id=str(
                                interaction.guild.id) if interaction.guild else None,
                            topic=topic,
                            operation="no_questions_found")
                return

            blocks = []
            current_block = f"📚 Questions for `{topic}`:\n"

            for i, q in enumerate(questions, start=1):
                line = f"{i}. {q['question']} (Answer: {q['correct_answer']})\n"
                if len(current_block) + len(line) > 2000:
                    blocks.append(current_block)
                    current_block = ""
                current_block += line

            if current_block:
                blocks.append(current_block)

            await interaction.followup.send(blocks[0], ephemeral=True)
            for block in blocks[1:]:
                await interaction.followup.send(block, ephemeral=True)

        except Exception:
            try:
                await interaction.followup.send("❌ Error in /list_questions command.", ephemeral=True)
            except Exception:
                pass

    @tree.command(name="delete_question", description="Delete a question by ID (Professors only)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(topic="Topic name", id="Question ID (string)")
    @app_commands.autocomplete(topic=autocomplete_topics)
    async def delete_question_command(interaction: Interaction, topic: str, id: str):
        if not await professor_verification(interaction):
            return
        if not await safe_defer(interaction, thinking=True, ephemeral=True):
            return

        try:
            update_last_interaction(interaction.guild.id)

            delete_question(interaction.guild.id, topic, id)
            await interaction.followup.send(f"🗑️ Deleted question with ID `{id}` from `{topic}`", ephemeral=True)

        except Exception as e:
            try:
                await interaction.followup.send(f"❌ Failed to delete question: {e}", ephemeral=True)
            except Exception:
                pass

    @tree.command(name="delete_all_questions", description="Delete all questions from a topic (Professors only)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(topic="Topic name", confirm="Set to true to confirm deleting all questions")
    @app_commands.autocomplete(topic=autocomplete_topics)
    async def delete_all_questions_command(interaction: Interaction, topic: str, confirm: bool):
        if not await professor_verification(interaction):
            return
        if not await safe_defer(interaction, thinking=True, ephemeral=True):
            return

        try:
            update_last_interaction(interaction.guild.id)

            if not confirm:
                await interaction.followup.send(
                    "⚠️ Deletion cancelled. Run the command again with `confirm=True` to remove all questions from this topic.",
                    ephemeral=True,
                )
                return

            deleted_count = delete_all_questions_by_topic(interaction.guild.id, topic)

            if deleted_count == 0:
                await interaction.followup.send(
                    f"📭 Topic `{topic}` has no questions to delete.",
                    ephemeral=True,
                )
                return

            await interaction.followup.send(
                f"🗑️ Deleted {deleted_count} questions from `{topic}`.",
                ephemeral=True,
            )

        except Exception as e:
            try:
                await interaction.followup.send(f"❌ Failed to delete all questions: {e}", ephemeral=True)
            except Exception:
                pass

    @tree.command(name="generate_questions", description="Generate multiple questions for a topic (Professors only)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(topic="Topic name", qty="Quantity of new questions", type="Question type")
    @app_commands.autocomplete(topic=autocomplete_topics, type=autocomplete_question_type)
    async def generate_questions_command(interaction: Interaction, topic: str, qty: int, type: str):
        if not await professor_verification(interaction):
            return
        if not await safe_defer(interaction, thinking=True, ephemeral=True):
            return

        try:
            update_last_interaction(interaction.guild.id)

            guild_id = interaction.guild.id
            topic_data = get_topic_by_name(guild_id, topic)

            topic_name = topic_data["title"]
            topic_id = topic_data["topic_id"]
            topic_storage_url = topic_data["document_storage_url"]

            str_to_enum = {
                "Multiple Choice": QuestionType.MULTIPLE_CHOICE,
                "True or False": QuestionType.TRUE_FALSE
            }

            if type not in str_to_enum:
                raise ValueError(f"'{type}' is not a valid QuestionType")

            question_type = str_to_enum[type]

            generated = await generate_questions_from_pdf(
                topic_name, topic_id, guild_id, topic_storage_url, 50, question_type)
            if generated:
                await interaction.followup.send(f"📭 Questions generated from `{topic_name}`", ephemeral=True)
            else:
                interaction.extras["command_failed"] = True
                await interaction.followup.send(
                    f"⚠️ Could not generate questions from `{topic_name}` right now (OpenRouter failed or requires credits).",
                    ephemeral=True
                )

        except Exception as e:
            try:
                await interaction.followup.send(f"❌ Failed to generate questions: {e}", ephemeral=True)
            except Exception:
                pass
