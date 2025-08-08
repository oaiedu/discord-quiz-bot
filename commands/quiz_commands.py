import logging
import random
from discord import app_commands, Interaction, ButtonStyle
import discord
from discord.ui import View, Button

from repositories.question_repository import update_question_stats
from repositories.server_repository import atualizar_ultima_interacao_servidor
from repositories.stats_repository import guardar_estadistica
from repositories.topic_repository import obter_preguntas_por_topic
from utils.enum import QuestionType
from utils.utils import obtener_temas_autocompletado, registrar_user_estadistica

class QuizButton(Button):
    def __init__(self, label: str, correct_answer: str, on_click_callback, parent_view: View):
        super().__init__(label=label, style=ButtonStyle.primary)
        self.correct_answer = correct_answer
        self.on_click_callback = on_click_callback
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        is_correct = await self.on_click_callback(interaction, self.label, self.correct_answer)

        for item in self.parent_view.children:
            item.disabled = True

        if is_correct:
            self.style = ButtonStyle.success
        else:
            self.style = ButtonStyle.danger

        await interaction.response.edit_message(view=self.parent_view)

        self.parent_view.stop()

class QuizView(View):
    def __init__(self, alternativas, correct_answer, on_click_callback, timeout=60):
        super().__init__(timeout=timeout)
        for letra in alternativas:
            self.add_item(QuizButton(letra, correct_answer, on_click_callback, self))

def register(tree: app_commands.CommandTree):
    
    @tree.command(name="quiz", description="Take a quiz with 5 questions on a topic")
    @app_commands.describe(nombre_topico="Topic name")
    @app_commands.autocomplete(nombre_topico=obtener_temas_autocompletado)
    async def quiz(interaction: discord.Interaction, nombre_topico: str):
        if interaction.guild:
            atualizar_ultima_interacao_servidor(interaction.guild.id)

        try:
            preguntas_data = obter_preguntas_por_topic(interaction.guild.id, nombre_topico)

            if not preguntas_data:
                await interaction.response.send_message(f"❌ There are no questions registered for the topic `{nombre_topico}`.")
                return

            preguntas = random.sample(preguntas_data, min(5, len(preguntas_data)))
            
            await interaction.response.send_message("📋 Starting the quiz...", ephemeral=True)
            
            respostas_usuario = []
            async def handle_answer(interaction_inner, escolha, correta):
                if interaction.user.id != interaction_inner.user.id:
                    await interaction_inner.response.send_message("This quiz isn't for you!", ephemeral=True)
                    return False

                respostas_usuario.append((escolha.upper(), correta.upper()))
                return escolha.upper() == correta.upper()

            for idx, p in enumerate(preguntas):
                data = p.to_dict()
                question_id = p.id
                tipo = data.get('question_type', 'True/False')
                texto = f"**{idx+1}. {data.get('question', '')}**"

                alternativas = data.get('alternatives', {}) if tipo == QuestionType.MULTIPLE_CHOICE.value else {'T': 'True', 'F': 'False'}

                for letra, alt_texto in alternativas.items():
                    texto += f"\n{letra}. {alt_texto}"

                correta = (
                    data.get('correct_answer', '') if tipo == 'Multiple Choice'
                    else ('T' if data.get('resposta', 'V').upper().startswith('V') else 'F')
                )

                async def answer_callback(interaction_inner, escolha, correta, question_id=question_id, p=p):
                    if interaction.user.id != interaction_inner.user.id:
                        await interaction_inner.response.send_message("This quiz isn't for you!", ephemeral=True)
                        return False

                    is_correct = escolha.upper() == correta.upper()
                    respostas_usuario.append((escolha.upper(), correta.upper()))

                    try:
                        update_question_stats(
                            guild_id=interaction.guild.id,
                            topic_id=p.reference.parent.parent.id,
                            question_id=question_id,
                            correct=is_correct
                        )
                    except Exception as err:
                        logging.warning(f"Erro ao atualizar stats da pergunta {question_id}: {err}")

                    return is_correct

                view = QuizView(alternativas, correta, answer_callback)
                await interaction.followup.send(texto, view=view, ephemeral=True)

                timeout = await view.wait()
                if timeout:
                    await interaction.followup.send("⏰ Time's up for this question.")
                    return

            resultado = "\n📊 Results:\n"
            correctas = 0

            for i, (r, correta) in enumerate(respostas_usuario):
                if r == correta:
                    resultado += f"✅ {i+1}. Correct\n"
                    correctas += 1
                else:
                    resultado += f"❌ {i+1}. Incorrect (Correct answer: {correta})\n"

            resultado += f"\n🏁 You answered correctly {correctas} out of {len(preguntas)} questions."
            await interaction.followup.send(resultado, ephemeral=True)

            tipos_perguntas = set()
            for p in preguntas:
                tipo = p.to_dict().get('question_type', 'True/False')
                tipos_perguntas.add(tipo)

            lista_tipos = list(tipos_perguntas)

            registrar_user_estadistica(interaction.user, nombre_topico, correctas, len(preguntas), lista_tipos)
            guardar_estadistica(interaction.guild.id, interaction.user, nombre_topico, correctas, len(preguntas))

        except Exception as e:
            logging.error(f"Error during quiz: {e}")
            await interaction.response.send_message("❌ An error occurred during the quiz.")
