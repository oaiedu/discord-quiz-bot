from discord import app_commands, Interaction
import discord
import logging
import os

from repositories.topic_repository import criar_topico_sem_perguntas, obter_topics_por_servidor, save_topic_pdf
from utils.enum import QuestionType
from utils.utils import actualizar_ultima_interaccion, is_professor
from utils.llm_utils import generar_preguntas_desde_pdf

RUTA_DOCS = "docs"

# Função salvar pdf no storage
async def save_pdf(interaction: Interaction, archivo: discord.Attachment, nombre_topico: str):
    try:
        if not archivo.filename.endswith(".pdf"):
            await interaction.followup.send("❌ Solo se permiten archivos PDF.")
            return

        os.makedirs(RUTA_DOCS, exist_ok=True)
        ruta_pdf = os.path.join(RUTA_DOCS, f"{nombre_topico}.pdf")
        await archivo.save(ruta_pdf)        
        
        pdf_url = save_topic_pdf(ruta_pdf, interaction.guild.id)
        print(pdf_url)
        
        if not pdf_url:
            await interaction.response.send_message("❌ No hay temas disponibles todavía.") 
        
        if os.path.exists(ruta_pdf):
            os.remove(ruta_pdf)
            
        return pdf_url
            
    except Exception as e:
        logging.error(f"Erro ao carregar tópicos: {e}")
        

def register(tree: app_commands.CommandTree):
    
    ### 
    # EXIBIR TODOS OS TÓPICOS 
    ###
    @tree.command(name="topics", description="Muestra los temas disponibles para hacer quizzes")
    async def list_topics(interaction: discord.Interaction):
        actualizar_ultima_interaccion(interaction.guild.id)

        try:
            temas_docs = obter_topics_por_servidor(interaction.guild.id)

            if not temas_docs:
                await interaction.response.send_message("❌ No hay temas disponibles todavía.")
                return

            temas = "\n".join(f"- {doc.to_dict().get('title', 'Sem título')}" for doc in temas_docs)
            await interaction.response.send_message(f"📚 Temas disponibles:\n{temas}")
        except Exception as e:
            logging.error(f"Erro ao carregar tópicos: {e}")
            await interaction.response.send_message("❌ Erro ao carregar os temas.")

    ### 
    # SALVAR PDF NO STORAGE
    ###
    @tree.command(name="upload_pdf", description="Salva o PDF sem gerar perguntas")
    @app_commands.describe(nombre_topico="Nombre del tema para guardar el PDF", archivo="Archivo PDF con el contenido")
    async def upload_pdf(interaction: discord.Interaction, nombre_topico: str, archivo: discord.Attachment):
        try:
            actualizar_ultima_interaccion(interaction.guild.id)

            await interaction.response.defer(thinking=True)
            
            pdf_url = await save_pdf(interaction, archivo, nombre_topico)
            
            try:
                guild_id = interaction.guild.id
                criar_topico_sem_perguntas(guild_id, nombre_topico, pdf_url)
                await interaction.followup.send("🧠 Topico criado com sucesso, mas sem perguntas")
            except Exception as e:
                await interaction.followup.send(f"❌ Error al generar preguntas: {e}")
        except Exception as e:
            logging.error(f"Erro ao carregar tópicos: {e}")
            await interaction.response.send_message("❌ Erro ao carregar os temas.")
            
    ###
    # SALVAR PDF E GERAR PERGUNTAS AUTOMATICAMENTE
    ###        
    @tree.command(name="upload_topic", description="Sube un PDF y genera preguntas automáticamente")
    @app_commands.describe(nombre_topico="Nombre del tema para guardar el PDF", archivo="Archivo PDF con el contenido")
    async def upload_pdf_with_questions(interaction: discord.Interaction, nombre_topico: str, archivo: discord.Attachment):
        actualizar_ultima_interaccion(interaction.guild.id)

        await interaction.response.defer(thinking=True)

        pdf_url = await save_pdf(interaction, archivo, nombre_topico)

        try:
            guild_id = interaction.guild.id
            generar_preguntas_desde_pdf(nombre_topico, None, guild_id, pdf_url, 50, QuestionType.TRUE_FALSE)
            await interaction.followup.send("🧠 Preguntas generadas correctamente desde el PDF.")
        except Exception as e:
            await interaction.followup.send(f"❌ Error al generar preguntas: {e}")
