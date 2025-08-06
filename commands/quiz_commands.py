import logging
import random
from discord import app_commands, Interaction
import discord

import bot
from repositories.server_repository import atualizar_ultima_interacao_servidor
from repositories.topic_repository import obter_preguntas_por_topic
from utils.utils import obtener_temas_autocompletado, registrar_user_estadistica

def register(tree: app_commands.CommandTree):
    
    @tree.command(name="quiz", description="Haz un quiz de 5 preguntas sobre un tema")
    @app_commands.describe(nombre_topico="Nombre del tema")
    @app_commands.autocomplete(nombre_topico=obtener_temas_autocompletado)
    async def quiz(interaction: discord.Interaction, nombre_topico: str):
        if interaction.guild:
            atualizar_ultima_interacao_servidor(interaction.guild.id)

        try:
            preguntas_data = obter_preguntas_por_topic(interaction.guild.id, nombre_topico)

            if not preguntas_data:
                await interaction.response.send_message(f"❌ No hay preguntas registradas para el tema `{nombre_topico}`.")
                return

            preguntas = random.sample(preguntas_data, min(5, len(preguntas_data)))
            texto_quiz = "📝 Responde con V o F (por ejemplo: `VFVFV`):\n"
            for idx, p in enumerate(preguntas):
                data = p.to_dict()
                texto_quiz += f"\n{idx+1}. {data.get('pregunta', '')}"

            await interaction.response.send_message(texto_quiz)

            def check(m):
                return (
                    m.author == interaction.user and
                    m.channel.id == interaction.channel_id and
                    len(m.content.strip()) == len(preguntas)
                )

            try:
                respuesta = await bot.wait_for("message", check=check, timeout=60.0)
                respuesta_str = respuesta.content.strip().upper()
            except:
                await interaction.followup.send("⏰ Tiempo agotado. Intenta nuevamente.")
                return

            resultado = "\n📊 Resultados:\n"
            correctas = 0
            for i, r in enumerate(respuesta_str):
                correcta = preguntas[i].to_dict().get('respuesta', 'V').upper()

                if r == correcta:
                    resultado += f"✅ {i+1}. Correcto\n"
                    correctas += 1
                else:
                    resultado += f"❌ {i+1}. Incorrecto (Respuesta correcta: {correcta})\n"

            resultado += f"\n🏁 Has acertado {correctas} de {len(preguntas)} preguntas."
            await interaction.followup.send(resultado)

            registrar_user_estadistica(interaction.user, nombre_topico, correctas, len(preguntas))

        except Exception as e:
            logging.error(f"Erro ao realizar quiz: {e}")
            await interaction.response.send_message("❌ Ocurrió un error durante el quiz.")