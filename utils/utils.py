# utils/utils.py
import discord
from discord import Interaction, app_commands
from typing import List, Union

from utils.structured_logging import structured_logger as logger
from repositories.topic_repository import get_topics_by_server
from repositories.user_repository import register_user_history
from repositories.server_repository import update_server_last_interaction
from utils.enum import QuestionType

ROLE_PROFESSOR = "faculty"


def is_professor(interaction: discord.Interaction) -> bool:
    return interaction.guild and any(
        role.name.lower() == ROLE_PROFESSOR.lower()
        for role in interaction.user.roles
    )


def update_last_interaction(guild_id: int):
    update_server_last_interaction(guild_id)


def get_topics_for_autocomplete(guild_id: int):
    documents = get_topics_by_server(guild_id)
    return [doc.to_dict().get("title", "Untitled") for doc in documents]


async def autocomplete_topics(interaction: discord.Interaction, current: str):
    try:
        topics = get_topics_for_autocomplete(interaction.guild.id) or []
        return [
            app_commands.Choice(name=topic, value=topic)
            for topic in topics if current.lower() in topic.lower()
        ][:25]
    except Exception as e:
        logger.error(f"❌ Error in autocomplete_topics: {e}", exc_info=True)
        print(f"❌ Error in autocomplete_topics: {e}")
        return []


async def autocomplete_TF(interaction, current: str):
    return [
        app_commands.Choice(name="T", value="T"),
        app_commands.Choice(name="F", value="F"),
    ]

async def autocomplete_question_type(
    interaction: Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=qt.name.replace(
            "_", " ").title(), value=qt.value)
        for qt in QuestionType
        if current.lower() in qt.name.lower()
    ]


def register_user_statistics(
    user: discord.User,
    topic_id: str,
    correct: int,
    total: int,
    types: Union[str, List[str]]
):
    if isinstance(types, str):
        types = [types]
    register_user_history(
        user_id=user.id,
        guild_id=user.guild.id,
        user_name=user.name,
        topic_id=topic_id,
        correct=correct,
        total=total,
        types=types,
    )
    
    
def log_command_event(level: str, interaction, message: str, operation: str, **kwargs):
    """
    Centraliza o logging estruturado para comandos de slash.

    Args:
        level (str): Nível do log ("info", "error", "warning", "debug", "critical").
        interaction (discord.Interaction): O objeto da interação do Discord.
        message (str): Mensagem principal do log.
        operation (str): Tipo de operação (ex.: "command_execution", "command_success", "command_error").
        **kwargs: Campos extras opcionais (ex.: error_type, error_message).
    """

    log_func = getattr(logger, level, logger.info)

    log_func(
        message,
        command=interaction.command.name if interaction.command else None,
        user_id=str(interaction.user.id),
        username=interaction.user.display_name,
        guild_id=str(interaction.guild.id) if interaction.guild else None,
        guild_name=interaction.guild.name if interaction.guild else None,
        channel_id=str(interaction.channel.id) if interaction.channel else None,
        is_professor=is_professor(interaction),
        operation=operation,
        **kwargs
    )
    
async def professor_verification(interaction: Interaction):
    
    if not is_professor(interaction):
        await interaction.response.send_message(
            "⛔ This command is for professors only.", ephemeral=True
        )
                
        logger.warning(
            f"❌ Unauthorized user attempted /user_rank: {interaction.user.display_name}",
            command="user_rank",
            user_id=str(interaction.user.id),
            username=interaction.user.display_name,
            guild_id=str(
                interaction.guild.id) if interaction.guild else None,
            operation="permission_denied"
        )
        return    
