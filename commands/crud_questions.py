import os
import json
import discord
import uuid  # Certifique-se de importar no topo do arquivo
from discord import app_commands, Interaction

ROL_PROFESOR = "faculty"
PREGUNTAS_JSON = "preguntas.json"


# Funciones auxiliares
def read_questions():
    if not os.path.exists(PREGUNTAS_JSON):
        return {}
    with open(PREGUNTAS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def write_questions(data):
    with open(PREGUNTAS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def is_professor(interaction: Interaction) -> bool:
    return interaction.guild and any(
        role.name.lower() == ROL_PROFESOR.lower()
        for role in interaction.user.roles
    )


async def obtener_temas_autocompletado(interaction: Interaction, current: str):
    data = read_questions()
    return [
        app_commands.Choice(name=tema, value=tema)
        for tema in data.keys() if current.lower() in tema.lower()
    ][:25]  # Máximo 25 opciones


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
        if not is_professor(interaction):
            await interaction.response.send_message("⛔ This command is for professors only.", ephemeral=True)
            return

        if answer.upper() not in ["V", "F"]:
            await interaction.response.send_message("❌ Answer must be 'V' or 'F'", ephemeral=True)
            return

        data = read_questions()
        if topic not in data:
            data[topic] = []

        nova_pergunta = {
            "pregunta": question,
            "respuesta": answer.upper(),
            "id": str(uuid.uuid4())  # Gera um ID único
        }

        data[topic].append(nova_pergunta)
        write_questions(data)

        await interaction.response.send_message(
            f"✅ Question added to `{topic}` with ID: `{nova_pergunta['id']}`.",
            ephemeral=True
        )

    @tree.command(name="list_questions", description="List questions for a topic (Professors only)")
    @app_commands.describe(topic="Topic name")
    @app_commands.autocomplete(topic=obtener_temas_autocompletado)
    async def list_questions(interaction: Interaction, topic: str):
        if not is_professor(interaction):
            await interaction.response.send_message("⛔ This command is for professors only.", ephemeral=True)
            return

        data = read_questions()
        if topic not in data or not data[topic]:
            await interaction.response.send_message(f"📭 No questions found for `{topic}`.", ephemeral=True)
            return

        preguntas = data[topic]
        bloques = []
        bloque_actual = f"📚 Questions for `{topic}`:\n"

        for i, q in enumerate(preguntas, start=1):
            linea = f"{i}. {q['pregunta']} (Answer: {q['respuesta']}, ID: `{q['id']}`)\n"
            if len(bloque_actual) + len(linea) > 2000:
                bloques.append(bloque_actual)
                bloque_actual = ""
            bloque_actual += linea

        if bloque_actual:
            bloques.append(bloque_actual)

        # Enviar o primeiro bloco como resposta e os demais como follow-ups
        await interaction.response.send_message(bloques[0], ephemeral=True)
        for bloque in bloques[1:]:
            await interaction.followup.send(bloque, ephemeral=True)

    @tree.command(name="delete_question", description="Delete a question by ID (Professors only)")
    @app_commands.describe(topic="Topic name", id="Question ID")
    @app_commands.autocomplete(topic=obtener_temas_autocompletado)
    async def delete_question(interaction: Interaction, topic: str, id: str):
        if not is_professor(interaction):
            await interaction.response.send_message("⛔ This command is for professors only.", ephemeral=True)
            return

        try:
            UUID(id)  # valida formato UUID
        except ValueError:
            await interaction.response.send_message("❌ Invalid question ID format.", ephemeral=True)
            return

        data = read_questions()
        if topic not in data:
            await interaction.response.send_message("❌ Topic not found.", ephemeral=True)
            return

        preguntas = data[topic]
        for i, q in enumerate(preguntas):
            if q.get("id") == id:
                deleted = preguntas.pop(i)
                write_questions(data)
                await interaction.response.send_message(f"🗑️ Deleted question: `{deleted['pregunta']}`", ephemeral=True)
                return

        await interaction.response.send_message(f"❌ No question with ID `{id}` found in `{topic}`.", ephemeral=True)
