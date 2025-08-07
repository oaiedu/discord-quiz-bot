# utils/utils.py
import discord
from discord import Interaction, app_commands
from typing import List, Union

from repositories.topic_repository import obter_topics_por_servidor
from repositories.user_repository import registrar_historico_usuario
from repositories.server_repository import atualizar_ultima_interacao_servidor
from utils.enum import QuestionType

ROL_PROFESOR = "faculty"

def is_professor(interaction: discord.Interaction) -> bool:
    return interaction.guild and any(
        role.name.lower() == ROL_PROFESOR.lower()
        for role in interaction.user.roles
    )

def actualizar_ultima_interaccion(guild_id: int):
    atualizar_ultima_interacao_servidor(guild_id)

def obter_topics_para_autocompletar(guild_id: int):
    documentos = obter_topics_por_servidor(guild_id)
    return [doc.to_dict().get("title", "Sem título") for doc in documentos]

async def obtener_temas_autocompletado(interaction: discord.Interaction, current: str):
    temas = obter_topics_para_autocompletar(interaction.guild.id)
    return [
        app_commands.Choice(name=tema, value=tema)
        for tema in temas if current.lower() in tema.lower()
    ][:25]
    
async def autocomplete_question_type(
    interaction: Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=qt.name.replace("_", " ").title(), value=qt.value)
        for qt in QuestionType
        if current.lower() in qt.name.lower()
    ]

def registrar_user_estadistica(user: discord.User, topic_id: str, aciertos: int, total: int, types: Union[str, List[str]]):
    if isinstance(types, str):
        types = [types]
    registrar_historico_usuario(
        user_id=user.id,
        guild_id=user.guild.id,
        user_name=user.name,
        topic_id=topic_id,
        acertos=aciertos,
        total=total,
        types=types,
    )
