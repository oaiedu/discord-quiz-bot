from firebase_init import db, SERVER_TIMESTAMP
import logging

def registrar_servidor(guild):
    try:
        db.collection("servers").document(str(guild.id)).set({
            "owner_id": str(guild.owner_id),
            "server_id": str(guild.id),
            "joined_at": SERVER_TIMESTAMP,
            "status": "Active"
        })
        logging.info(f"✅ Servidor {guild.id} registrado com sucesso.")
    except Exception as e:
        logging.error(f"❌ Erro ao registrar servidor {guild.id}: {e}")

def atualizar_status_servidor(guild_id, status):
    try:
        db.collection("servers").document(str(guild_id)).update({
            "status": status
        })
        logging.info(f"✅ Status do servidor {guild_id} atualizado para '{status}'.")
    except Exception as e:
        logging.error(f"❌ Erro ao atualizar status do servidor {guild_id}: {e}")

def atualizar_ultima_interacao_servidor(guild_id: int):
    try:
        db.collection("servers").document(str(guild_id)).update({
            "last_interaction": SERVER_TIMESTAMP
        })
        logging.info(f"🕒 Última interação atualizada para servidor {guild_id}")
    except Exception as e:
        logging.error(f"❌ Erro ao atualizar última interação: {e}")

def desativar_servidor(guild_id: int):
    try:
        db.collection("servers").document(str(guild_id)).update({
            "status": "disabled"
        })
        logging.info(f"📁 Status do servidor {guild_id} atualizado para 'disabled'")
    except Exception as e:
        logging.error(f"❌ Erro ao desativar servidor: {e}")
