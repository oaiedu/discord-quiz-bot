import logging
from discord import app_commands, Interaction

from repositories.question_repository import (list_questions_by_topic, add_question, delete_question)
from repositories.topic_repository import get_topic_by_name
from utils.enum import QuestionType
from utils.llm_utils import generate_questions_from_pdf
from utils.structured_logging import structured_logger as logger
from utils.utils import professor_verification, update_last_interaction, autocomplete_question_type, is_professor, autocomplete_topics, autocomplete_TF

# Register commands


def register(tree: app_commands.CommandTree):

    @tree.command(name="add_question", description="Add a question to a topic (Professors only)")
    @app_commands.describe(
        topic="Topic name",
        question="Question text",
        answer="Correct answer (T or F)"
    )
    @app_commands.autocomplete(topic=autocomplete_topics, answer=autocomplete_TF)
    async def add_question_command(interaction: Interaction, topic: str, question: str, answer: str):
        # Immediate defer to avoid Discord timeout (3 seconds)
        await interaction.response.defer(thinking=True, ephemeral=True)

        # Log command execution
        logger.info(f"🔍 Command /add_question executed by {interaction.user.display_name}",
                    command="add_question",
                    user_id=str(interaction.user.id),
                    username=interaction.user.display_name,
                    guild_id=str(
                        interaction.guild.id) if interaction.guild else None,
                    guild_name=interaction.guild.name if interaction.guild else None,
                    channel_id=str(
                        interaction.channel.id) if interaction.channel else None,
                    is_professor=is_professor(interaction),
                    topic=topic,
                    operation="command_execution")

        try:
            update_last_interaction(interaction.guild.id)

            professor_verification(interaction)

            if answer.upper() not in ["T", "F"]:
                await interaction.followup.send("❌ Answer must be 'V' or 'F'", ephemeral=True)
                logger.warning(f"❌ Invalid answer in /add_question: {answer}",
                               command="add_question",
                               user_id=str(interaction.user.id),
                               username=interaction.user.display_name,
                               guild_id=str(
                                   interaction.guild.id) if interaction.guild else None,
                               invalid_answer=answer,
                               operation="validation_error")
                return

            new_id = add_question(interaction.guild.id,
                                  topic, question, answer.upper())
            await interaction.followup.send(
                f"✅ Question added to `{topic}` with ID: `{new_id}`.",
                ephemeral=True
            )

            # Log success
            logger.info(f"✅ Command /add_question successfully completed for {interaction.user.display_name}",
                        command="add_question",
                        user_id=str(interaction.user.id),
                        username=interaction.user.display_name,
                        guild_id=str(
                            interaction.guild.id) if interaction.guild else None,
                        topic=topic,
                        question_id=new_id,
                        operation="command_success")

        except Exception as e:
            logger.error(f"❌ Error in /add_question command: {e}",
                         command="add_question",
                         user_id=str(interaction.user.id),
                         username=interaction.user.display_name,
                         guild_id=str(
                             interaction.guild.id) if interaction.guild else None,
                         topic=topic,
                         error_type=type(e).__name__,
                         error_message=str(e),
                         operation="command_error")

            try:
                await interaction.followup.send(f"❌ Failed to add question: {e}", ephemeral=True)
            except Exception:
                pass

    @tree.command(name="list_questions", description="List questions for a topic (Professors only)")
    @app_commands.describe(topic="Topic name")
    @app_commands.autocomplete(topic=autocomplete_topics)
    async def list_questions_command(interaction: Interaction, topic: str):
        await interaction.response.defer(thinking=True, ephemeral=True)

        logger.info(f"🔍 Command /list_questions executed by {interaction.user.display_name}",
                    command="list_questions",
                    user_id=str(interaction.user.id),
                    username=interaction.user.display_name,
                    guild_id=str(
                        interaction.guild.id) if interaction.guild else None,
                    guild_name=interaction.guild.name if interaction.guild else None,
                    channel_id=str(
                        interaction.channel.id) if interaction.channel else None,
                    is_professor=is_professor(interaction),
                    topic=topic,
                    operation="command_execution")

        try:
            update_last_interaction(interaction.guild.id)

            professor_verification(interaction)

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

            logger.info(f"✅ Command /list_questions successfully completed for {interaction.user.display_name}",
                        command="list_questions",
                        user_id=str(interaction.user.id),
                        username=interaction.user.display_name,
                        guild_id=str(
                            interaction.guild.id) if interaction.guild else None,
                        topic=topic,
                        questions_count=len(questions),
                        operation="command_success")

        except Exception as e:
            logger.error(f"❌ Error in /list_questions command: {e}",
                         command="list_questions",
                         user_id=str(interaction.user.id),
                         username=interaction.user.display_name,
                         guild_id=str(
                             interaction.guild.id) if interaction.guild else None,
                         topic=topic,
                         error_type=type(e).__name__,
                         error_message=str(e),
                         operation="command_error",)

            try:
                await interaction.followup.send("❌ Error in /list_questions command.", ephemeral=True)
            except Exception:
                pass

    @tree.command(name="delete_question", description="Delete a question by ID (Professors only)")
    @app_commands.describe(topic="Topic name", id="Question ID (string)")
    @app_commands.autocomplete(topic=autocomplete_topics)
    async def delete_question_command(interaction: Interaction, topic: str, id: str):
        await interaction.response.defer(thinking=True, ephemeral=True)

        logger.info(f"🔍 Command /delete_question executed by {interaction.user.display_name}",
                    command="delete_question",
                    user_id=str(interaction.user.id),
                    username=interaction.user.display_name,
                    guild_id=str(
                        interaction.guild.id) if interaction.guild else None,
                    guild_name=interaction.guild.name if interaction.guild else None,
                    channel_id=str(
                        interaction.channel.id) if interaction.channel else None,
                    is_professor=is_professor(interaction),
                    topic=topic,
                    question_id=id,
                    operation="command_execution")

        try:
            update_last_interaction(interaction.guild.id)

            professor_verification(interaction)

            delete_question(interaction.guild.id, topic, id)
            await interaction.followup.send(f"🗑️ Deleted question with ID `{id}` from `{topic}`", ephemeral=True)

            logger.info(f"✅ Command /delete_question successfully completed for {interaction.user.display_name}",
                        command="delete_question",
                        user_id=str(interaction.user.id),
                        username=interaction.user.display_name,
                        guild_id=str(
                            interaction.guild.id) if interaction.guild else None,
                        topic=topic,
                        question_id=id,
                        operation="command_success")

        except Exception as e:
            logger.error(f"❌ Error in /delete_question command: {e}",
                         command="delete_question",
                         user_id=str(interaction.user.id),
                         username=interaction.user.display_name,
                         guild_id=str(
                             interaction.guild.id) if interaction.guild else None,
                         topic=topic,
                         question_id=id,
                         error_type=type(e).__name__,
                         error_message=str(e),
                         operation="command_error")

            try:
                await interaction.followup.send(f"❌ Failed to delete question: {e}", ephemeral=True)
            except Exception:
                pass

    @tree.command(name="generate_questions", description="Generate multiple questions for a topic (Professors only)")
    @app_commands.describe(topic="Topic name", qty="Quantity of new questions", type="Question type")
    @app_commands.autocomplete(topic=autocomplete_topics, type=autocomplete_question_type)
    async def generate_questions_command(interaction: Interaction, topic: str, qty: int, type: str):
        await interaction.response.defer(thinking=True, ephemeral=True)

        logger.info(f"🔍 Command /generate_questions executed by {interaction.user.display_name}",
                    command="generate_questions",
                    user_id=str(interaction.user.id),
                    username=interaction.user.display_name,
                    guild_id=str(
                        interaction.guild.id) if interaction.guild else None,
                    guild_name=interaction.guild.name if interaction.guild else None,
                    channel_id=str(
                        interaction.channel.id) if interaction.channel else None,
                    is_professor=is_professor(interaction),
                    topic=topic,
                    quantity=qty,
                    question_type=type,
                    operation="command_execution")

        try:
            update_last_interaction(interaction.guild.id)

            professor_verification(interaction)

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

            generate_questions_from_pdf(
                topic_name, topic_id, guild_id, topic_storage_url, 50, question_type)
            await interaction.followup.send(f"📭 Questions generated from `{topic_name}`", ephemeral=True)

            logger.info(f"✅ Command /generate_questions successfully completed for {interaction.user.display_name}",
                        command="generate_questions",
                        user_id=str(interaction.user.id),
                        username=interaction.user.display_name,
                        guild_id=str(
                            interaction.guild.id) if interaction.guild else None,
                        topic=topic_name,
                        topic_id=topic_id,
                        quantity=qty,
                        question_type=type,
                        operation="command_success")

        except Exception as e:
            logger.error(f"❌ Error in /generate_questions command: {e}",
                         command="generate_questions",
                         user_id=str(interaction.user.id),
                         username=interaction.user.display_name,
                         guild_id=str(
                             interaction.guild.id) if interaction.guild else None,
                         topic=topic,
                         quantity=qty,
                         question_type=type,
                         error_type=type(e).__name__,
                         error_message=str(e),
                         operation="command_error")

            try:
                await interaction.followup.send(f"❌ Failed to generate questions: {e}", ephemeral=True)
            except Exception:
                pass
