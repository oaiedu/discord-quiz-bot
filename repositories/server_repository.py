from firebase_init import db, SERVER_TIMESTAMP
import logging

def registrar_servidor(guild):
    return db.collection("servers").document(str(guild.id)).set({
        "owner_id": str(guild.owner_id),
        "server_id": str(guild.id),
        "joined_at": SERVER_TIMESTAMP,
        "status": "Active"
    })

def atualizar_status_servidor(guild_id, status):
    return db.collection("servers").document(str(guild_id)).update({
        "status": status
    })

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
        print(f"📁 Status do servidor {guild_id} atualizado para 'disabled'")
    except Exception as e:
        logging.error(f"❌ Erro ao desativar servidor: {e}")

