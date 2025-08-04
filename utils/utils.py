# utils/utils.py
import discord

from repositories.user_repository import registrar_historico_usuario

from repositories.server_repository import atualizar_ultima_interacao_servidor


def actualizar_ultima_interaccion(guild_id: int):
    atualizar_ultima_interacao_servidor(guild_id)

def registrar_user_estadistica(user: discord.User, topic_id: str, aciertos: int, total: int):
    registrar_historico_usuario(
        user_id=user.id,
        guild_id=user.guild.id,
        user_name=user.name,
        topic_id=topic_id,
        acertos=aciertos,
        total=total
    )
