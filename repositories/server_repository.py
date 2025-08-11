from firebase_init import db, SERVER_TIMESTAMP
from utils.structured_logging import structured_logger as logger

def registrar_servidor(guild):
    try:
        db.collection("servers").document(str(guild.id)).set({
            "owner_id": str(guild.owner_id),
            "server_id": str(guild.id),
            "joined_at": SERVER_TIMESTAMP,
            "status": "Active"
        })
        logger.info(f"✅ Servidor {guild.id} registrado com sucesso.", 
                   guild_id=str(guild.id), 
                   operation="server_registration")
    except Exception as e:
        logger.error(f"❌ Erro ao registrar servidor {guild.id}: {e}", 
                    guild_id=str(guild.id), 
                    operation="server_registration",
                    error_type=type(e).__name__)

def atualizar_status_servidor(guild_id, status):
    try:
        db.collection("servers").document(str(guild_id)).update({
            "status": status
        })
        logger.info(f"✅ Status do servidor {guild_id} atualizado para '{status}'.",
                   guild_id=str(guild_id),
                   operation="server_status_update",
                   new_status=status)
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar status do servidor {guild_id}: {e}",
                    guild_id=str(guild_id),
                    operation="server_status_update",
                    error_type=type(e).__name__)

def atualizar_ultima_interacao_servidor(guild_id: int):
    try:
        db.collection("servers").document(str(guild_id)).update({
            "last_interaction": SERVER_TIMESTAMP
        })
        logger.info(f"🕒 Última interação atualizada para servidor {guild_id}",
                   guild_id=str(guild_id),
                   operation="server_interaction_update")
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar última interação: {e}",
                    guild_id=str(guild_id),
                    operation="server_interaction_update",
                    error_type=type(e).__name__)

def desativar_servidor(guild_id: int):
    try:
        db.collection("servers").document(str(guild_id)).update({
            "status": "disabled"
        })
        logger.info(f"📁 Status do servidor {guild_id} atualizado para 'disabled'",
                   guild_id=str(guild_id),
                   operation="server_deactivation")
    except Exception as e:
        logger.error(f"❌ Erro ao desativar servidor: {e}",
                    guild_id=str(guild_id),
                    operation="server_deactivation",
                    error_type=type(e).__name__)
