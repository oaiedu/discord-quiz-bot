import os
import json
from discord import app_commands, Interaction
import discord

ROL_PROFESOR = "faculty"
PREGUNTAS_JSON = "preguntas.json"


def read_questions():
    if not os.path.exists(PREGUNTAS_JSON):
        return {}
    with open(PREGUNTAS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def write_questions(data):
    with open(PREGUNTAS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def is_professor(interaction: Interaction) -> bool:
    return interaction.guild and any(role.name.lower() == ROL_PROFESOR.lower() for role in interaction.user.roles)


def register(tree: app_commands.CommandTree):
    @tree.command(name="add_question", description="Add a question to a topic (Professors only)")
    @app_commands.describe(
        topic="Topic name",
        question="Question text",
        answer="Correct answer (V or F)"
    )
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
        data[topic].append({"pregunta": question, "respuesta": answer.upper()})
        write_questions(data)

        await interaction.response.send_message(f"✅ Question added to `{topic}`.")

    @tree.command(name="list_questions", description="List questions for a topic (Professors only)")
    @app_commands.describe(topic="Topic name")
    async def list_questions(interaction: Interaction, topic: str):
        if not is_professor(interaction):
            await interaction.response.send_message("⛔ This command is for professors only.", ephemeral=True)
            return

        data = read_questions()
        if topic not in data or not data[topic]:
            await interaction.response.send_message(f"📭 No questions found for `{topic}`.")
            return

        mensaje = f"📚 Questions for `{topic}`:\n"
        for i, q in enumerate(data[topic]):
            mensaje += f"{i+1}. {q['pregunta']} (Answer: {q['respuesta']})\n"

        await interaction.response.send_message(mensaje)

    @tree.command(name="delete_question", description="Delete a question by index (Professors only)")
    @app_commands.describe(topic="Topic name", index="Question number (starts at 1)")
    async def delete_question(interaction: Interaction, topic: str, index: int):
        if not is_professor(interaction):
            await interaction.response.send_message("⛔ This command is for professors only.", ephemeral=True)
            return

        data = read_questions()
        if topic not in data or index < 1 or index > len(data[topic]):
            await interaction.response.send_message("❌ Invalid topic or index.", ephemeral=True)
            return

        deleted = data[topic].pop(index - 1)
        write_questions(data)
        await interaction.response.send_message(f"🗑️ Deleted question: `{deleted['pregunta']}`")
