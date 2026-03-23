from discord import app_commands, Interaction
import discord
import logging
import os
import json

from repositories.topic_repository import create_topic_without_questions, create_topic_with_questions, get_topics_by_server, save_topic_pdf
from utils.structured_logging import structured_logger as logger
from utils.enum import QuestionType
from utils.utils import professor_verification, update_last_interaction, is_professor, safe_defer, autocomplete_question_type
from utils.llm_utils import generate_questions_from_pdf

DOCS_PATH = "docs"


def _normalize_uploaded_questions(raw_data, question_type: QuestionType):
    if isinstance(raw_data, dict):
        for key in ("questions", "items", "data"):
            if isinstance(raw_data.get(key), list):
                raw_data = raw_data[key]
                break

    if not isinstance(raw_data, list):
        raise ValueError("JSON must be a list of questions (or an object with a 'questions' list).")

    if len(raw_data) == 0:
        raise ValueError("JSON question list is empty.")

    normalized = []
    for index, item in enumerate(raw_data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Question #{index} must be a JSON object.")

        question_text = str(item.get("question", "")).strip()
        if not question_text:
            raise ValueError(f"Question #{index} is missing 'question'.")

        raw_answer_value = item.get("answer")
        if raw_answer_value in (None, ""):
            raw_answer_value = item.get("correct_answer")
        if raw_answer_value in (None, ""):
            raw_answer_value = item.get("correctAnswer")

        if question_type == QuestionType.TRUE_FALSE:
            raw_answer = str(raw_answer_value or "").strip().upper()
            if raw_answer.startswith("T"):
                normalized_answer = "T"
            elif raw_answer.startswith("F"):
                normalized_answer = "F"
            else:
                raise ValueError(
                    f"Question #{index} must include answer as True/False or T/F."
                )

            normalized.append({
                "question": question_text,
                "answer": normalized_answer,
                "alternatives": {"T": "True", "F": "False"}
            })

        else:
            options = item.get("alternatives") or item.get("options")
            if not isinstance(options, dict):
                raise ValueError(f"Question #{index} must include 'alternatives' or 'options' object.")

            # Allow lowercase keys from user-generated JSON (a/b/c/d)
            options = {str(k).upper(): v for k, v in options.items()}

            required_keys = ["A", "B", "C", "D"]
            normalized_options = {}
            for key in required_keys:
                value = str(options.get(key, "")).strip()
                if not value:
                    raise ValueError(f"Question #{index} is missing option '{key}'.")
                normalized_options[key] = value

            raw_answer = str(raw_answer_value or "").strip().upper()
            if raw_answer not in required_keys:
                raise ValueError(f"Question #{index} answer must be one of A/B/C/D.")

            normalized.append({
                "question": question_text,
                "answer": raw_answer,
                "alternatives": normalized_options
            })

    return normalized

# Function to save PDF to storage
async def save_pdf(interaction: Interaction, file: discord.Attachment, topic_name: str):
    try:
        if not await professor_verification(interaction):
            return None

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
        if not await professor_verification(interaction):
            return
        if not await safe_defer(interaction, thinking=True, ephemeral=False):
            return

        try:
            # --- Protection for Issue #1494 ---
            try:
                update_last_interaction(interaction.guild.id)
            except Exception as e:
                logging.warning(f"Failed to update interaction: {e}")

            topics = get_topics_by_server(interaction.guild.id, include_empty=False)

            if not topics:
                await interaction.followup.send("📭 There are no topics with questions available yet.")
                return

            topics_list = "\n".join(
                f"- {doc.to_dict().get('title', 'Untitled')}" for doc in topics)

            await interaction.followup.send(f"📚 Available topics:\n{topics_list}")

        except Exception as e:
            logging.error(f"Error loading topics: {e}")
            try:
                await interaction.followup.send("❌ Error loading topics.")
            except Exception as send_error:
                logging.error(f"Failed to send error message: {send_error}")

    ###
    # UPLOAD PDF WITHOUT GENERATING QUESTIONS
    ###
    @tree.command(name="upload_pdf", description="Saves the PDF without generating questions")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(topic_name="Name of the topic to save the PDF under", file="PDF file with content")
    async def upload_pdf_command(interaction: discord.Interaction, topic_name: str, file: discord.Attachment):
        if not await professor_verification(interaction):
            return
        if not await safe_defer(interaction, thinking=True, ephemeral=True):
            return

        try:
            # --- Protection for Issue #1494 ---
            try:
                update_last_interaction(interaction.guild.id)
            except Exception as e:
                logging.warning(f"Failed to update interaction: {e}")

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
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(topic_name="Name of the topic to save the PDF under", file="PDF file with content")
    async def upload_pdf_with_questions(interaction: discord.Interaction, topic_name: str, file: discord.Attachment):
        if not await professor_verification(interaction):
            return
        if not await safe_defer(interaction, thinking=True, ephemeral=True):
            return

        try:
            # --- Protection for Issue #1494 ---
            try:
                update_last_interaction(interaction.guild.id)
            except Exception as e:
                logging.warning(f"Failed to update interaction: {e}")

            pdf_url = await save_pdf(interaction, file, topic_name)

            if pdf_url is None:
                return # Stop execution here if upload failed

            guild_id = interaction.guild.id
            generated = await generate_questions_from_pdf(
                topic_name, None, guild_id, pdf_url, 50, QuestionType.TRUE_FALSE)
            if generated:
                await interaction.followup.send("🧠 Questions successfully generated from the PDF.", ephemeral=True)
            else:
                interaction.extras["command_failed"] = True
                await interaction.followup.send(
                    "⚠️ I could not generate questions from this PDF right now (OpenRouter failed or rate-limited).",
                    ephemeral=True
                )

        except Exception as e:
            try:
                await interaction.followup.send(f"❌ Error generating questions: {e}", ephemeral=True)
            except Exception:
                pass

    @tree.command(name="upload_questions_json", description="Upload a JSON file with questions and create/update a topic")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        topic_name="Topic name for these questions",
        type="Question type inside the JSON file",
        file="JSON file with the questions"
    )
    @app_commands.autocomplete(type=autocomplete_question_type)
    async def upload_questions_json_command(
        interaction: discord.Interaction,
        topic_name: str,
        type: str,
        file: discord.Attachment,
    ):
        if not await professor_verification(interaction):
            return
        if not await safe_defer(interaction, thinking=True, ephemeral=True):
            return

        try:
            try:
                update_last_interaction(interaction.guild.id)
            except Exception as e:
                logging.warning(f"Failed to update interaction: {e}")

            if not file.filename.lower().endswith(".json"):
                await interaction.followup.send("❌ Only .json files are allowed.", ephemeral=True)
                return

            str_to_enum = {
                "Multiple Choice": QuestionType.MULTIPLE_CHOICE,
                "True or False": QuestionType.TRUE_FALSE,
            }
            if type not in str_to_enum:
                await interaction.followup.send("❌ Invalid question type.", ephemeral=True)
                return
            question_type = str_to_enum[type]

            raw_bytes = await file.read()
            try:
                raw_payload = json.loads(raw_bytes.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as parse_error:
                await interaction.followup.send(
                    f"❌ Invalid JSON file: {parse_error}",
                    ephemeral=True,
                )
                return

            try:
                questions = _normalize_uploaded_questions(raw_payload, question_type)
            except ValueError as validation_error:
                await interaction.followup.send(
                    f"❌ JSON validation error: {validation_error}",
                    ephemeral=True,
                )
                return

            topic_id = create_topic_with_questions(
                guild_id=interaction.guild.id,
                topic_title=topic_name,
                topic_id=None,
                new_questions=questions,
                document_url="",
                qty=len(questions),
                qtype=question_type,
            )

            if not topic_id:
                interaction.extras["command_failed"] = True
                await interaction.followup.send("❌ Could not save topic/questions to Firestore.", ephemeral=True)
                return

            await interaction.followup.send(
                f"✅ Uploaded {len(questions)} questions to topic `{topic_name}` ({question_type.value}).",
                ephemeral=True,
            )

        except Exception as e:
            interaction.extras["command_failed"] = True
            try:
                await interaction.followup.send(f"❌ Error uploading JSON questions: {e}", ephemeral=True)
            except Exception:
                pass