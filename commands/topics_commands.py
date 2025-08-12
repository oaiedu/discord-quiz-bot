from discord import app_commands, Interaction
import discord
import logging
import os

from repositories.topic_repository import criar_topico_sem_perguntas, obter_topics_por_servidor, save_topic_pdf
from utils.structured_logging import structured_logger as logger
from utils.enum import QuestionType
from utils.utils import actualizar_ultima_interaccion, is_professor
from utils.llm_utils import generar_preguntas_desde_pdf

RUTA_DOCS = "docs"

# Function to save PDF to storage
async def save_pdf(interaction: Interaction, archivo: discord.Attachment, nombre_topico: str):
    try:
                        
        if not is_professor(interaction):
            await interaction.response.send_message("\u26d4 This command is only available to professors.", ephemeral=True)
            return
        
        if not archivo.filename.endswith(".pdf"):
            await interaction.followup.send("❌ Only PDF files are allowed.", ephemeral=True)
            return

        os.makedirs(RUTA_DOCS, exist_ok=True)
        ruta_pdf = os.path.join(RUTA_DOCS, f"{nombre_topico}.pdf")
        await archivo.save(ruta_pdf)        
        
        pdf_url = save_topic_pdf(ruta_pdf, interaction.guild.id)
        print(pdf_url)
        
        if not pdf_url:
            await interaction.response.send_message("❌ No topics available yet.", ephemeral=True) 
        
        if os.path.exists(ruta_pdf):
            os.remove(ruta_pdf)
            
        return pdf_url
            
    except Exception as e:
        logging.error(f"Error loading topics: {e}")
        

def register(tree: app_commands.CommandTree):
    
    ### 
    # SHOW ALL TOPICS
    ###
    @tree.command(name="topics", description="Displays the available topics for quizzes")
    async def list_topics(interaction: discord.Interaction):
        # Log INMEDIATO antes de cualquier operación
        logger.info(f"🔍 Comando /topics ejecutado por {interaction.user.display_name}", 
                   command="topics",
                   user_id=str(interaction.user.id),
                   username=interaction.user.display_name,
                   guild_id=str(interaction.guild.id),
                   guild_name=interaction.guild.name,
                   channel_id=str(interaction.channel.id),
                   is_professor=is_professor(interaction),
                   operation="command_execution")
        
        try:
            # Verificar permisos PRIMERO y responder rápido
            if not is_professor(interaction):
                logger.warning("Access denied - non-professor attempted to use topics command",
                              command="topics",
                              user_id=str(interaction.user.id),
                              username=interaction.user.display_name,
                              guild_id=str(interaction.guild.id),
                              operation="access_denied")
                await interaction.response.send_message("\u26d4 This command is only available to professors.", ephemeral=True)
                return

            # Defer para operaciones que pueden tomar tiempo
            await interaction.response.defer(thinking=True)
            
            # Ahora hacer operaciones que pueden tomar tiempo
            actualizar_ultima_interaccion(interaction.guild.id)
            temas_docs = obter_topics_por_servidor(interaction.guild.id)

            if not temas_docs:
                logger.info("No topics available for guild",
                           command="topics",
                           user_id=str(interaction.user.id),
                           username=interaction.user.display_name,
                           guild_id=str(interaction.guild.id),
                           operation="no_topics_found")
                await interaction.followup.send("❌ No topics available yet.")
                return

            topic_count = len(temas_docs)
            temas = "\n".join(f"- {doc.to_dict().get('title', 'Untitled')}" for doc in temas_docs)
            logger.info("Topics command completed successfully",
                       command="topics",
                       user_id=str(interaction.user.id),
                       username=interaction.user.display_name,
                       guild_id=str(interaction.guild.id),
                       guild_name=interaction.guild.name,
                       channel_id=str(interaction.channel.id),
                       is_professor=is_professor(interaction),
                       operation="command_success",
                       topic_count=topic_count)
            
            await interaction.followup.send(f"📚 Available topics:\n{temas}")
            
        except Exception as e:
            logger.error(f"❌ Error en comando /topics: {e}",
                        command="topics",
                        user_id=str(interaction.user.id),
                        username=interaction.user.display_name,
                        guild_id=str(interaction.guild.id),
                        guild_name=interaction.guild.name,
                        channel_id=str(interaction.channel.id),
                        is_professor=is_professor(interaction),
                        operation="command_error",
                        error_type=type(e).__name__,
                        error_message=str(e))
            logging.error(f"Error loading topics: {e}")
            
            # Verificar si ya respondimos a la interacción
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Error loading topics.")
                else:
                    await interaction.followup.send("❌ Error loading topics.", ephemeral=True)
            except:
                # Si falla completamente, al menos loggeamos el error
                logging.error("Failed to send error message to user")

    ### 
    # SAVE PDF TO STORAGE
    ###
    @tree.command(name="upload_pdf", description="Saves the PDF without generating questions")
    @app_commands.describe(nombre_topico="Name of the topic to save the PDF under", archivo="PDF file with content")
    async def upload_pdf(interaction: discord.Interaction, nombre_topico: str, archivo: discord.Attachment):
        # DEFER INMEDIATO para evitar timeout de Discord (3 segundos)
        await interaction.response.defer(thinking=True, ephemeral=True)
        
        # Log del comando ejecutado
        logger.info(f"🔍 Comando /upload_pdf ejecutado por {interaction.user.display_name}",
                   command="upload_pdf",
                   user_id=str(interaction.user.id),
                   username=interaction.user.display_name,
                   guild_id=str(interaction.guild.id) if interaction.guild else None,
                   guild_name=interaction.guild.name if interaction.guild else None,
                   channel_id=str(interaction.channel.id) if interaction.channel else None,
                   is_professor=is_professor(interaction),
                   topic=nombre_topico,
                   file_name=archivo.filename if archivo else None,
                   operation="command_execution")
        
        try:
            actualizar_ultima_interaccion(interaction.guild.id)

            if not is_professor(interaction):
                await interaction.followup.send("⛔ This command is only available to professors.", ephemeral=True)
                logger.warning(f"❌ Usuario sin permisos intentó usar /upload_pdf: {interaction.user.display_name}",
                              command="upload_pdf",
                              user_id=str(interaction.user.id),
                              username=interaction.user.display_name,
                              guild_id=str(interaction.guild.id) if interaction.guild else None,
                              operation="permission_denied")
                return
            
            pdf_url = await save_pdf(interaction, archivo, nombre_topico)
            
            try:
                guild_id = interaction.guild.id
                criar_topico_sem_perguntas(guild_id, nombre_topico, pdf_url)
                await interaction.followup.send("🧠 Topic created successfully, but without questions.", ephemeral=True)
                
                # Log de éxito del comando
                logger.info(f"✅ Comando /upload_pdf completado exitosamente para {interaction.user.display_name}",
                           command="upload_pdf",
                           user_id=str(interaction.user.id),
                           username=interaction.user.display_name,
                           guild_id=str(interaction.guild.id) if interaction.guild else None,
                           topic=nombre_topico,
                           file_name=archivo.filename if archivo else None,
                           pdf_url=pdf_url,
                           operation="command_success")
                           
            except Exception as e:
                await interaction.followup.send(f"❌ Error generating questions: {e}", ephemeral=True)
                logger.error(f"❌ Error creando tópico en /upload_pdf: {e}",
                            command="upload_pdf",
                            user_id=str(interaction.user.id),
                            username=interaction.user.display_name,
                            guild_id=str(interaction.guild.id) if interaction.guild else None,
                            topic=nombre_topico,
                            error_type=type(e).__name__,
                            error_message=str(e),
                            operation="topic_creation_error")
                            
        except Exception as e:
            logger.error(f"❌ Error en comando /upload_pdf: {e}",
                        command="upload_pdf",
                        user_id=str(interaction.user.id),
                        username=interaction.user.display_name,
                        guild_id=str(interaction.guild.id) if interaction.guild else None,
                        topic=nombre_topico,
                        error_type=type(e).__name__,
                        error_message=str(e),
                        operation="command_error")
            
            try:
                await interaction.followup.send("❌ Error loading topics.", ephemeral=True)
            except Exception:
                pass
            
    ###
    # SAVE PDF AND GENERATE QUESTIONS AUTOMATICALLY
    ###        
    @tree.command(name="upload_topic", description="Uploads a PDF and automatically generates questions")
    @app_commands.describe(nombre_topico="Name of the topic to save the PDF under", archivo="PDF file with content")
    async def upload_pdf_with_questions(interaction: discord.Interaction, nombre_topico: str, archivo: discord.Attachment):
        # DEFER INMEDIATO para evitar timeout de Discord (3 segundos)
        await interaction.response.defer(thinking=True, ephemeral=True)
        
        # Log del comando ejecutado
        logger.info(f"🔍 Comando /upload_topic ejecutado por {interaction.user.display_name}",
                   command="upload_topic",
                   user_id=str(interaction.user.id),
                   username=interaction.user.display_name,
                   guild_id=str(interaction.guild.id) if interaction.guild else None,
                   guild_name=interaction.guild.name if interaction.guild else None,
                   channel_id=str(interaction.channel.id) if interaction.channel else None,
                   is_professor=is_professor(interaction),
                   topic=nombre_topico,
                   file_name=archivo.filename if archivo else None,
                   operation="command_execution")
        
        try:
            actualizar_ultima_interaccion(interaction.guild.id)
        
            if not is_professor(interaction):
                await interaction.followup.send("⛔ This command is only available to professors.", ephemeral=True)
                logger.warning(f"❌ Usuario sin permisos intentó usar /upload_topic: {interaction.user.display_name}",
                              command="upload_topic",
                              user_id=str(interaction.user.id),
                              username=interaction.user.display_name,
                              guild_id=str(interaction.guild.id) if interaction.guild else None,
                              operation="permission_denied")
                return

            pdf_url = await save_pdf(interaction, archivo, nombre_topico)

            guild_id = interaction.guild.id
            generar_preguntas_desde_pdf(nombre_topico, None, guild_id, pdf_url, 50, QuestionType.TRUE_FALSE)
            await interaction.followup.send("🧠 Questions successfully generated from the PDF.", ephemeral=True)
            
            # Log de éxito del comando
            logger.info(f"✅ Comando /upload_topic completado exitosamente para {interaction.user.display_name}",
                       command="upload_topic",
                       user_id=str(interaction.user.id),
                       username=interaction.user.display_name,
                       guild_id=str(interaction.guild.id) if interaction.guild else None,
                       topic=nombre_topico,
                       file_name=archivo.filename if archivo else None,
                       pdf_url=pdf_url,
                       questions_generated=50,
                       operation="command_success")
                       
        except Exception as e:
            logger.error(f"❌ Error en comando /upload_topic: {e}",
                        command="upload_topic",
                        user_id=str(interaction.user.id),
                        username=interaction.user.display_name,
                        guild_id=str(interaction.guild.id) if interaction.guild else None,
                        topic=nombre_topico,
                        error_type=type(e).__name__,
                        error_message=str(e),
                        operation="command_error")
            
            try:
                await interaction.followup.send(f"❌ Error generating questions: {e}", ephemeral=True)
            except Exception:
                pass
