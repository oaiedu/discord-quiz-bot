import logging
import random
from discord import app_commands, Interaction
import discord

from repositories.server_repository import atualizar_ultima_interacao_servidor
from repositories.stats_repository import guardar_estadistica
from repositories.topic_repository import obter_preguntas_por_topic
from utils.enum import QuestionType
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
            texto_quiz = "📝 Responda cada pregunta conforme indicado (ex: `VFVFV` ou `ABCDC`):\n"
            
            await interaction.response.send_message("📋 Iniciando o quiz...", ephemeral=True)

            for idx, p in enumerate(preguntas):
                data = p.to_dict()
                tipo = data.get('question_type', 'True/False')
                texto = f"**{idx+1}. {data.get('question', '')}**"

                if tipo == QuestionType.MULTIPLE_CHOICE.value:
                    alternativas = data.get('alternatives', {})
                    for letra, alt_texto in alternativas.items():
                        texto += f"\n{letra}. {alt_texto}"

                await interaction.followup.send(texto, ephemeral=True)

            await interaction.followup.send(texto_quiz, ephemeral=True)

            def check(m):
                return (
                    m.author == interaction.user and
                    m.channel.id == interaction.channel_id and
                    len(m.content.strip()) == len(preguntas)
                )

            try:
                resposta = await interaction.client.wait_for("message", check=check, timeout=60.0)
                resposta_str = resposta.content.strip().upper()
            except:
                await interaction.followup.send("⏰ Tiempo agotado. Intenta nuevamente.")
                return

            resultado = "\n📊 Resultados:\n"
            correctas = 0
            for i, r in enumerate(resposta_str):
                pergunta = preguntas[i].to_dict()
                tipo = pergunta.get('question_type', 'True/False')

                if tipo == 'Multiple Choice':
                    correta = pergunta.get('correct_answer', '').upper()
                else:
                    correta = pergunta.get('resposta', 'V').upper()
                    correta = 'V' if correta.startswith('V') else 'F'

                if r == correta:
                    resultado += f"✅ {i+1}. Correcto\n"
                    correctas += 1
                else:
                    resultado += f"❌ {i+1}. Incorrecto (Respuesta correcta: {correta})\n"

            resultado += f"\n🏁 Has acertado {correctas} de {len(preguntas)} preguntas."
            await interaction.followup.send(resultado, ephemeral=True)

            tipos_perguntas = set()
            for p in preguntas:
                tipo = p.to_dict().get('question_type', 'True/False')
                tipos_perguntas.add(tipo)

            lista_tipos = list(tipos_perguntas)

            registrar_user_estadistica(interaction.user, nombre_topico, correctas, len(preguntas), lista_tipos)
            guardar_estadistica(interaction.guild.id, interaction.user, nombre_topico, correctas, len(preguntas))

        except Exception as e:
            logging.error(f"Erro ao realizar quiz: {e}")
            await interaction.response.send_message("❌ Ocurrió un error durante el quiz.")