from discord import app_commands, Interaction

from repositories.question_repository import (
    listar_perguntas_por_topico,
    adicionar_pergunta,
    deletar_pergunta
)
from repositories.topic_repository import obter_topics_para_autocompletar
from utils.utils import actualizar_ultima_interaccion

ROL_PROFESOR = "faculty"

# Função auxiliar para verificar permissão
def is_professor(interaction: Interaction) -> bool:
    return interaction.guild and any(
        role.name.lower() == ROL_PROFESOR.lower()
        for role in interaction.user.roles
    )

# Autocompletar com base no Firestore
async def obtener_temas_autocompletado(interaction: Interaction, current: str):
    temas = obter_topics_para_autocompletar(interaction.guild.id)
    return [
        app_commands.Choice(name=tema, value=tema)
        for tema in temas if current.lower() in tema.lower()
    ][:25]

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
