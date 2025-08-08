from discord import app_commands, Interaction

from repositories.question_repository import ( listar_perguntas_por_topico, adicionar_pergunta, deletar_pergunta )
from repositories.topic_repository import get_topic_by_name
from utils.enum import QuestionType
from utils.llm_utils import generar_preguntas_desde_pdf
from utils.utils import actualizar_ultima_interaccion, autocomplete_question_type, is_professor, obtener_temas_autocompletado

# Registro de comandos
def register(tree: app_commands.CommandTree):

    @tree.command(name="add_question", description="Add a question to a topic (Professors only)")
    @app_commands.describe(
        topic="Topic name",
        question="Question text",
        answer="Correct answer (V or F)"
    )
    @app_commands.autocomplete(topic=obtener_temas_autocompletado)
    async def add_question(interaction: Interaction, topic: str, question: str, answer: str):
        actualizar_ultima_interaccion(interaction.guild.id)

        if not is_professor(interaction):
            await interaction.response.send_message("⛔ This command is for professors only.", ephemeral=True)
            return

        if answer.upper() not in ["V", "F"]:
            await interaction.response.send_message("❌ Answer must be 'V' or 'F'", ephemeral=True)
            return

        try:
            nova_id = adicionar_pergunta(interaction.guild.id, topic, question, answer.upper())
            await interaction.response.send_message(
                f"✅ Question added to `{topic}` with ID: `{nova_id}`.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to add question: {e}",
                ephemeral=True
            )

    @tree.command(name="list_questions", description="List questions for a topic (Professors only)")
    @app_commands.describe(topic="Topic name")
    @app_commands.autocomplete(topic=obtener_temas_autocompletado)
    async def list_questions(interaction: Interaction, topic: str):
        actualizar_ultima_interaccion(interaction.guild.id)

        if not is_professor(interaction):
            await interaction.response.send_message("⛔ This command is for professors only.", ephemeral=True)
            return

        perguntas = listar_perguntas_por_topico(interaction.guild.id, topic)

        if not perguntas:
            await interaction.response.send_message(f"📭 No questions found for `{topic}`.", ephemeral=True)
            return

        blocos = []
        bloco_atual = f"📚 Questions for `{topic}`:\n"

        for i, q in enumerate(perguntas, start=1):
            linha = f"{i}. {q['pregunta']} (Answer: {q['respuesta']})\n"
            if len(bloco_atual) + len(linha) > 2000:
                blocos.append(bloco_atual)
                bloco_atual = ""
            bloco_atual += linha

        if bloco_atual:
            blocos.append(bloco_atual)

        await interaction.response.send_message(blocos[0], ephemeral=True)
        for bloco in blocos[1:]:
            await interaction.followup.send(bloco, ephemeral=True)

    @tree.command(name="delete_question", description="Delete a question by ID (Professors only)")
    @app_commands.describe(topic="Topic name", id="Question ID (string)")
    @app_commands.autocomplete(topic=obtener_temas_autocompletado)
    async def delete_question(interaction: Interaction, topic: str, id: str):
        actualizar_ultima_interaccion(interaction.guild.id)

        if not is_professor(interaction):
            await interaction.response.send_message("⛔ This command is for professors only.", ephemeral=True)
            return

        try:
            deletar_pergunta(interaction.guild.id, topic, id)
            await interaction.response.send_message(f"🗑️ Deleted question with ID `{id}` from `{topic}`", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to delete question: {e}", ephemeral=True)
            
    @tree.command(name="generate_questions", description="Generate multiple questions for a topic (Professors only)")
    @app_commands.describe(topic="Topic name", qty="Quantity of new questions", type="Type os questions")
    @app_commands.autocomplete(topic=obtener_temas_autocompletado, type=autocomplete_question_type)
    async def generate_questions(interaction: Interaction, topic: str, qty: int, type: str):
        actualizar_ultima_interaccion(interaction.guild.id)

        if not is_professor(interaction):
            await interaction.response.send_message("⛔ This command is for professors only.", ephemeral=True)
            return
        
        try:
            await interaction.response.defer(thinking=True, ephemeral=True)
            
            guild_id = interaction.guild.id
            
            topic = get_topic_by_name(guild_id, topic)
            
            topic_name = topic["title"]
            topic_id = topic["topic_id"]
            topic_storage_url = topic["document_storage_url"]
                    
            str_to_enum = {
                "Multiple Choice": QuestionType.MULTIPLE_CHOICE,
                "True or False": QuestionType.TRUE_FALSE
            }

            if type not in str_to_enum:
                raise ValueError(f"'{type}' is not a valid QuestionType")

            question_type = str_to_enum[type]
            
            generar_preguntas_desde_pdf(topic_name, topic_id, guild_id, topic_storage_url, 50, question_type)
            await interaction.followup.send(f"📭 Questions generated from `{topic_name}`", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to generate questions: {e}", ephemeral=True)
