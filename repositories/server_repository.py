from firebase_init import db, SERVER_TIMESTAMP
from utils.structured_logging import structured_logger as logger


def _server_metadata_payload(guild):
    return {
        "owner_id": str(guild.owner_id) if guild.owner_id else None,
        "server_id": str(guild.id),
        "server_name": guild.name,
        "member_count": guild.member_count or 0,
        "description": guild.description,
    }


def register_server(guild):
    try:
        doc_ref = db.collection("servers").document(str(guild.id))
        snapshot = doc_ref.get()

        payload = {
            **_server_metadata_payload(guild),
            "status": "Active",
        }

        if not snapshot.exists:
            payload["joined_at"] = SERVER_TIMESTAMP

        doc_ref.set(payload, merge=True)
        logger.info(f"✅ Server {guild.id} successfully registered.",
                    guild_id=str(guild.id),
                    operation="server_registration")
    except Exception as e:
        logger.error(f"❌ Error while registering server {guild.id}: {e}",
                     guild_id=str(guild.id),
                     operation="server_registration",
                     error_type=type(e).__name__)


def update_server_status(guild_id, status):
    try:
        db.collection("servers").document(str(guild_id)).update({
            "status": status
        })
        logger.info(f"✅ Server {guild_id} status updated to '{status}'.",
                    guild_id=str(guild_id),
                    operation="server_status_update",
                    new_status=status)
    except Exception as e:
        logger.error(f"❌ Error while updating server {guild_id} status: {e}",
                     guild_id=str(guild_id),
                     operation="server_status_update",
                     error_type=type(e).__name__)


def update_server_metadata(guild):
    try:
        db.collection("servers").document(str(guild.id)).set({
            **_server_metadata_payload(guild),
            "status": "Active",
            "updated_at": SERVER_TIMESTAMP,
        }, merge=True)
        logger.info(f"✅ Server metadata updated for {guild.id}.",
                    guild_id=str(guild.id),
                    operation="server_metadata_update")
    except Exception as e:
        logger.error(f"❌ Error while updating server metadata {guild.id}: {e}",
                     guild_id=str(guild.id),
                     operation="server_metadata_update",
                     error_type=type(e).__name__)


def update_server_last_interaction(guild_id: int):
    try:
        db.collection("servers").document(str(guild_id)).set({
            "server_id": str(guild_id),
            "status": "Active",
            "last_interaction": SERVER_TIMESTAMP
        }, merge=True)
        logger.info(f"🕒 Last interaction updated for server {guild_id}",
                    guild_id=str(guild_id),
                    operation="server_interaction_update")
    except Exception as e:
        logger.error(f"❌ Error while updating last interaction: {e}",
                     guild_id=str(guild_id),
                     operation="server_interaction_update",
                     error_type=type(e).__name__)


def deactivate_server(guild_id: int):
    try:
        db.collection("servers").document(str(guild_id)).update({
            "status": "disabled"
        })
        logger.info(f"📁 Server {guild_id} status updated to 'disabled'",
                    guild_id=str(guild_id),
                    operation="server_deactivation")
    except Exception as e:
        logger.error(f"❌ Error while deactivating server: {e}",
                     guild_id=str(guild_id),
                     operation="server_deactivation",
                     error_type=type(e).__name__)
