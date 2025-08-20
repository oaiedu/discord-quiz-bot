# utils/utils.py
import discord
from discord import Interaction, app_commands
from typing import List, Union

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
    topics = get_topics_for_autocomplete(interaction.guild.id)
    return [
        app_commands.Choice(name=topic, value=topic)
        for topic in topics if current.lower() in topic.lower()
    ][:25]


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
