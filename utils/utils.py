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


def get_interaction_role_names(interaction: discord.Interaction) -> list[str]:
    member = interaction.user
    if isinstance(member, discord.Member):
        return [role.name.lower() for role in member.roles]

    guild = interaction.guild
    data = getattr(interaction, "data", None) or {}
    member_data = data.get("member", {})
    role_ids = member_data.get("roles", [])

    if not guild or not role_ids:
        return []

    role_names = []
    for role_id in role_ids:
        role = guild.get_role(int(role_id))
        if role:
            role_names.append(role.name.lower())

    return role_names


def interaction_has_admin_permission(interaction: discord.Interaction) -> bool:
    member = interaction.user
    if isinstance(member, discord.Member):
        return member.guild_permissions.administrator

    data = getattr(interaction, "data", None) or {}
    member_data = data.get("member", {})
    permissions_value = member_data.get("permissions")
    if permissions_value is None:
        return False

    try:
        permissions = discord.Permissions(int(permissions_value))
    except (TypeError, ValueError):
        return False

    return permissions.administrator


def is_professor(interaction: discord.Interaction) -> bool:
    return bool(interaction.guild) and ROLE_PROFESSOR.lower() in get_interaction_role_names(interaction)


def update_last_interaction(guild_id: int):
    update_server_last_interaction(guild_id)


def get_topics_for_autocomplete(guild_id: int, *, include_empty: bool = True):
    documents = get_topics_by_server(guild_id, include_empty=include_empty)
    return [doc.to_dict().get("title", "Untitled") for doc in documents]


async def autocomplete_topics(interaction: discord.Interaction, current: str):
    try:
        topics = get_topics_for_autocomplete(interaction.guild.id, include_empty=False) or []
        return [
            app_commands.Choice(name=topic, value=topic)
            for topic in topics if current.lower() in topic.lower()
        ][:25]
    except Exception as e:
        logger.error(f"❌ Error in autocomplete_topics: {e}", exc_info=True)
        print(f"❌ Error in autocomplete_topics: {e}")
        return []


async def autocomplete_quiz_topics(interaction: discord.Interaction, current: str):
    try:
        topics = get_topics_for_autocomplete(interaction.guild.id, include_empty=False) or []
        return [
            app_commands.Choice(name=topic, value=topic)
            for topic in topics if current.lower() in topic.lower()
        ][:25]
    except Exception as e:
        logger.error(f"❌ Error in autocomplete_quiz_topics: {e}", exc_info=True)
        print(f"❌ Error in autocomplete_quiz_topics: {e}")
        return []


async def autocomplete_all_topics(interaction: discord.Interaction, current: str):
    try:
        topics = get_topics_for_autocomplete(interaction.guild.id, include_empty=True) or []
        return [
            app_commands.Choice(name=topic, value=topic)
            for topic in topics if current.lower() in topic.lower()
        ][:25]
    except Exception as e:
        logger.error(f"❌ Error in autocomplete_all_topics: {e}", exc_info=True)
        print(f"❌ Error in autocomplete_all_topics: {e}")
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
    Centralizes structured logging for slash commands.

    Args:
        level (str): Log level ("info", "error", "warning", "debug", "critical").
        interaction (discord.Interaction): The Discord interaction object.
        message (str): Main log message.
        operation (str): Type of operation (e.g., "command_execution", "command_success", "command_error").
        **kwargs: Optional extra fields (e.g., error_type, error_message).
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


async def safe_defer(interaction: Interaction, *, thinking: bool = True, ephemeral: bool = True) -> bool:
    if interaction.response.is_done():
        return True

    try:
        await interaction.response.defer(thinking=thinking, ephemeral=ephemeral)
        return True
    except discord.HTTPException as error:
        if error.code in (40060, 10062):
            log_command_event(
                "warning",
                interaction,
                f"⚠ Ignoring duplicate or expired interaction: {error}",
                operation="command_duplicate_interaction",
                error_type=type(error).__name__,
                error_message=str(error)
            )
            return False
        raise
    
async def professor_verification(interaction: Interaction) -> bool:
    if is_professor(interaction):
        return True

    if interaction.response.is_done():
        await interaction.followup.send(
            "⛔ This command is for professors only.", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "⛔ This command is for professors only.", ephemeral=True
        )

    logger.warning(
        f"❌ Unauthorized user attempted /{interaction.command.name if interaction.command else 'unknown'}: {interaction.user.display_name}",
        command=interaction.command.name if interaction.command else "unknown",
        user_id=str(interaction.user.id),
        username=interaction.user.display_name,
        guild_id=str(interaction.guild.id) if interaction.guild else None,
        operation="permission_denied"
    )
    return False
