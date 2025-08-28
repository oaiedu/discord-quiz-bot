from discord import app_commands, Interaction
import discord
import logging
import os

from repositories.topic_repository import create_topic_without_questions, get_topics_by_server, save_topic_pdf
from utils.structured_logging import structured_logger as logger
from utils.enum import QuestionType
from utils.utils import professor_verification, update_last_interaction, is_professor
from utils.llm_utils import generate_questions_from_pdf

DOCS_PATH = "docs"

# Function to save PDF to storage
async def save_pdf(interaction: Interaction, file: discord.Attachment, topic_name: str):
    try:
        professor_verification(interaction)

        if not file.filename.endswith(".pdf"):
            await interaction.followup.send("❌ Only PDF files are allowed.", ephemeral=True)
            return

        os.makedirs(DOCS_PATH, exist_ok=True)
        pdf_path = os.path.join(DOCS_PATH, f"{topic_name}.pdf")
        await file.save(pdf_path)

        pdf_url = save_topic_pdf(pdf_path, interaction.guild.id)
        print(pdf_url)

        if not pdf_url:
            await interaction.followup.send("❌ No topics available yet.", ephemeral=True)

        if os.path.exists(pdf_path):
            os.remove(pdf_path)

        return pdf_url

    except Exception as e:
        logging.error(f"Error saving PDF: {e}")


def register(tree: app_commands.CommandTree):

    ###
    # LIST ALL TOPICS
    ###
    @tree.command(name="topics", description="Displays the available topics for quizzes")
    async def list_topics(interaction: discord.Interaction):
        logger.info(f"🔍 /topics command executed by {interaction.user.display_name}",
                    command="topics",
                    user_id=str(interaction.user.id),
                    username=interaction.user.display_name,
                    guild_id=str(interaction.guild.id),
                    guild_name=interaction.guild.name,
                    channel_id=str(interaction.channel.id),
                    is_professor=is_professor(interaction),
                    operation="command_execution")

        try:
            if not is_professor(interaction):
                logger.warning("Access denied - non-professor attempted to use /topics command",
                               command="topics",
                               user_id=str(interaction.user.id),
                               username=interaction.user.display_name,
                               guild_id=str(interaction.guild.id),
                               operation="access_denied")
                await interaction.response.send_message("⛔ This command is only available to professors.", ephemeral=True)
                return

            await interaction.response.defer(thinking=True)

            update_last_interaction(interaction.guild.id)
            topics = get_topics_by_server(interaction.guild.id)

            professor_verification(interaction)

            topic_count = len(topics)
            topics_list = "\n".join(
                f"- {doc.to_dict().get('title', 'Untitled')}" for doc in topics)
            logger.info("Topics command completed successfully",
                        command="topics",
                        user_id=str(interaction.user.id),
                        username=interaction.user.display_name,
                        guild_id=str(interaction.guild.id),
                        guild_name=interaction.guild.name,
                        channel_id=str(interaction.channel.id),
                        is_professor=is_professor(interaction),
                        operation="command_success",
                        topic_count=topic_count)

            await interaction.followup.send(f"📚 Available topics:\n{topics_list}")

        except Exception as e:
            logger.error(f"❌ Error in /topics command: {e}",
                         command="topics",
                         user_id=str(interaction.user.id),
                         username=interaction.user.display_name,
                         guild_id=str(interaction.guild.id),
                         guild_name=str(interaction.guild.name),
                         channel_id=str(interaction.channel.id),
                         is_professor=is_professor(interaction),
                         operation="command_error",
                         error_type=type(e).__name__,
                         error_message=str(e))
            logging.error(f"Error loading topics: {e}")

            try:
                await interaction.followup.send("❌ Error loading topics.", ephemeral=True)
            except:
                logging.error("Failed to send error message to user")

    ###
    # UPLOAD PDF WITHOUT GENERATING QUESTIONS
    ###
    @tree.command(name="upload_pdf", description="Saves the PDF without generating questions")
    @app_commands.describe(topic_name="Name of the topic to save the PDF under", file="PDF file with content")
    async def upload_pdf_command(interaction: discord.Interaction, topic_name: str, file: discord.Attachment):
        await interaction.response.defer(thinking=True, ephemeral=True)

        logger.info(f"🔍 /upload_pdf command executed by {interaction.user.display_name}",
                    command="upload_pdf",
                    user_id=str(interaction.user.id),
                    username=interaction.user.display_name,
                    guild_id=str(
                        interaction.guild.id) if interaction.guild else None,
                    guild_name=interaction.guild.name if interaction.guild else None,
                    channel_id=str(
                        interaction.channel.id) if interaction.channel else None,
                    is_professor=is_professor(interaction),
                    topic=topic_name,
                    file_name=file.filename if file else None,
                    operation="command_execution")

        try:
            update_last_interaction(interaction.guild.id)

            professor_verification(interaction)

            pdf_url = await save_pdf(interaction, file, topic_name)

            try:
                guild_id = interaction.guild.id
                create_topic_without_questions(guild_id, topic_name, pdf_url)
                await interaction.followup.send("🧠 Topic created successfully, but without questions.", ephemeral=True)

                logger.info(f"✅ /upload_pdf command completed successfully for {interaction.user.display_name}",
                            command="upload_pdf",
                            user_id=str(interaction.user.id),
                            username=interaction.user.display_name,
                            guild_id=str(
                                interaction.guild.id) if interaction.guild else None,
                            topic=topic_name,
                            file_name=file.filename if file else None,
                            pdf_url=pdf_url,
                            operation="command_success")

            except Exception as e:
                await interaction.followup.send(f"❌ Error creating topic: {e}", ephemeral=True)
                logger.error(f"❌ Error creating topic in /upload_pdf: {e}",
                             command="upload_pdf",
                             user_id=str(interaction.user.id),
                             username=interaction.user.display_name,
                             guild_id=str(
                                 interaction.guild.id) if interaction.guild else None,
                             topic=topic_name,
                             error_type=type(e).__name__,
                             error_message=str(e),
                             operation="topic_creation_error")

        except Exception as e:
            logger.error(f"❌ Error in /upload_pdf command: {e}",
                         command="upload_pdf",
                         user_id=str(interaction.user.id),
                         username=interaction.user.display_name,
                         guild_id=str(
                             interaction.guild.id) if interaction.guild else None,
                         topic=topic_name,
                         error_type=type(e).__name__,
                         error_message=str(e),
                         operation="command_error")

            try:
                await interaction.followup.send("❌ Error loading topics.", ephemeral=True)
            except Exception:
                pass

    ###
    # UPLOAD PDF AND GENERATE QUESTIONS AUTOMATICALLY
    ###
    @tree.command(name="upload_topic", description="Uploads a PDF and automatically generates questions")
    @app_commands.describe(topic_name="Name of the topic to save the PDF under", file="PDF file with content")
    async def upload_pdf_with_questions(interaction: discord.Interaction, topic_name: str, file: discord.Attachment):
        await interaction.response.defer(thinking=True, ephemeral=True)

        logger.info(f"🔍 /upload_topic command executed by {interaction.user.display_name}",
                    command="upload_topic",
                    user_id=str(interaction.user.id),
                    username=interaction.user.display_name,
                    guild_id=str(
                        interaction.guild.id) if interaction.guild else None,
                    guild_name=interaction.guild.name if interaction.guild else None,
                    channel_id=str(
                        interaction.channel.id) if interaction.channel else None,
                    is_professor=is_professor(interaction),
                    topic=topic_name,
                    file_name=file.filename if file else None,
                    operation="command_execution")

        try:
            update_last_interaction(interaction.guild.id)

            professor_verification(interaction)

            pdf_url = await save_pdf(interaction, file, topic_name)

            guild_id = interaction.guild.id
            generate_questions_from_pdf(
                topic_name, None, guild_id, pdf_url, 50, QuestionType.TRUE_FALSE)
            await interaction.followup.send("🧠 Questions successfully generated from the PDF.", ephemeral=True)

            logger.info(f"✅ /upload_topic command completed successfully for {interaction.user.display_name}",
                        command="upload_topic",
                        user_id=str(interaction.user.id),
                        username=interaction.user.display_name,
                        guild_id=str(
                            interaction.guild.id) if interaction.guild else None,
                        topic=topic_name,
                        file_name=file.filename if file else None,
                        pdf_url=pdf_url,
                        questions_generated=50,
                        operation="command_success")

        except Exception as e:
            logger.error(f"❌ Error in /upload_topic command: {e}",
                         command="upload_topic",
                         user_id=str(interaction.user.id),
                         username=interaction.user.display_name,
                         guild_id=str(
                             interaction.guild.id) if interaction.guild else None,
                         topic=topic_name,
                         error_type=type(e).__name__,
                         error_message=str(e),
                         operation="command_error")

            try:
                await interaction.followup.send(f"❌ Error generating questions: {e}", ephemeral=True)
            except Exception:
                pass