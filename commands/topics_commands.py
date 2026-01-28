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
            await interaction.followup.send("❌ Storage Error: Failed to upload PDF.", ephemeral=True)
            return None # To ensure the calling function knows it failed

        if os.path.exists(pdf_path):
            os.remove(pdf_path)

        return pdf_url

    except Exception as e:
        logging.error(f"Error saving PDF: {e}")
        return None


def register(tree: app_commands.CommandTree):

    ###
    # LIST ALL TOPICS
    ###
    @tree.command(name="topics", description="Displays the available topics for quizzes")
    async def list_topics(interaction: discord.Interaction):
        try:
            professor_verification(interaction)

            await interaction.response.defer(thinking=True)

            # --- Protection for Issue #1494 ---
            try:
                update_last_interaction(interaction.guild.id)
            except Exception as e:
                logging.warning(f"Failed to update interaction: {e}")

            topics = get_topics_by_server(interaction.guild.id)

            professor_verification(interaction)

            topic_count = len(topics)
            topics_list = "\n".join(
                f"- {doc.to_dict().get('title', 'Untitled')}" for doc in topics)


            await interaction.followup.send(f"📚 Available topics:\n{topics_list}")

        except Exception as e:
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

        try:
            # --- Protection for Issue #1494 ---
            try:
                update_last_interaction(interaction.guild.id)
            except Exception as e:
                logging.warning(f"Failed to update interaction: {e}")

            professor_verification(interaction)

            pdf_url = await save_pdf(interaction, file, topic_name)

            if pdf_url is None:
                return # Stop execution here if upload failed

            try:
                guild_id = interaction.guild.id
                create_topic_without_questions(guild_id, topic_name, pdf_url)
                await interaction.followup.send("🧠 Topic created successfully, but without questions.", ephemeral=True)

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

        try:
            # --- Protection for Issue #1494 ---
            try:
                update_last_interaction(interaction.guild.id)
            except Exception as e:
                logging.warning(f"Failed to update interaction: {e}")

            professor_verification(interaction)

            pdf_url = await save_pdf(interaction, file, topic_name)

            if pdf_url is None:
                return # Stop execution here if upload failed

            guild_id = interaction.guild.id
            generate_questions_from_pdf(
                topic_name, None, guild_id, pdf_url, 50, QuestionType.TRUE_FALSE)
            await interaction.followup.send("🧠 Questions successfully generated from the PDF.", ephemeral=True)

        except Exception as e:
            try:
                await interaction.followup.send(f"❌ Error generating questions: {e}", ephemeral=True)
            except Exception:
                pass