import discord
from discord import app_commands, Interaction

from repositories.topic_repository import get_topic_by_name
from utils.llm_utils import generate_explanation_from_pdf
from utils.structured_logging import structured_logger as logger
from utils.utils import safe_defer, update_last_interaction, autocomplete_all_topics


def register(tree: app_commands.CommandTree):
    @tree.command(name="explain", description="Get a short AI explanation for a topic")
    @app_commands.describe(topic="Topic name")
    @app_commands.autocomplete(topic=autocomplete_all_topics)
    async def explain_command(interaction: Interaction, topic: str):
        if not await safe_defer(interaction, thinking=True, ephemeral=True):
            return

        try:
            if not interaction.guild:
                await interaction.followup.send(
                    "❌ This command can only be used inside a server.",
                    ephemeral=True,
                )
                return

            update_last_interaction(interaction.guild.id)

            topic_data = get_topic_by_name(interaction.guild.id, topic)
            if not topic_data:
                await interaction.followup.send(
                    f"❌ Topic '{topic}' not found.",
                    ephemeral=True,
                )
                return

            topic_name = topic_data.get("title", topic)
            pdf_url = topic_data.get("document_storage_url")
            if not pdf_url:
                await interaction.followup.send(
                    f"❌ Topic '{topic_name}' does not have a PDF associated yet.",
                    ephemeral=True,
                )
                return

            explanation = await generate_explanation_from_pdf(
                topic_name=topic_name,
                pdf_url=pdf_url,
                max_lines=10,
            )

            if not explanation:
                await interaction.followup.send(
                    f"⚠️ Could not generate an explanation for '{topic_name}' right now. Please try again.",
                    ephemeral=True,
                )
                return

            # Extra safety for Discord message size.
            safe_explanation = explanation[:1800].strip()

            await interaction.followup.send(
                f"📖 Explanation for {topic_name}:\n{safe_explanation}",
                ephemeral=True,
            )

        except Exception as e:
            logger.error(f"Error in /explain command: {e}", exc_info=True)
            try:
                await interaction.followup.send(
                    "❌ An error occurred while generating the explanation.",
                    ephemeral=True,
                )
            except Exception:
                pass