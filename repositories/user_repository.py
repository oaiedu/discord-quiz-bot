from typing import List
from firebase_init import db, SERVER_TIMESTAMP
from utils.structured_logging import structured_logger as logger
from firebase_admin import firestore
from datetime import datetime
import pytz


def register_guild_users(guild):
    try:
        batch = db.batch()
        for member in guild.members:
            if member.bot:
                continue
            doc_ref = db.collection("servers") \
                        .document(str(guild.id)) \
                        .collection("users") \
                        .document(str(member.id))
            batch.set(doc_ref, {
                "user_id": str(member.id),
                "name": member.name,
                "joined_bot_at": SERVER_TIMESTAMP
            })
        batch.commit()
        logger.info(f"✅ Users of server {guild.id} successfully registered.",
                    guild_id=str(guild.id),
                    operation="bulk_user_registration",
                    user_count=len([m for m in guild.members if not m.bot]))
    except Exception as e:
        logger.error(f"❌ Error registering users for server {guild.id}: {e}",
                     guild_id=str(guild.id),
                     operation="bulk_user_registration",
                     error_type=type(e).__name__)


def register_single_user(guild, member):
    try:
        if member.bot:
            return None

        doc_ref = db.collection("servers") \
                    .document(str(guild.id)) \
                    .collection("users") \
                    .document(str(member.id))

        if doc_ref.get().exists:
            logger.warning(f"⚠️ User {member.name} ({member.id}) is already registered.",
                           user_id=str(member.id),
                           guild_id=str(guild.id),
                           username=member.name,
                           operation="single_user_registration")
            return None

        doc_ref.set({
            "user_id": str(member.id),
            "name": member.name,
            "joined_bot_at": SERVER_TIMESTAMP
        })

        logger.info(f"✅ User {member.name} ({member.id}) successfully registered.",
                    user_id=str(member.id),
                    guild_id=str(guild.id),
                    username=member.name,
                    operation="single_user_registration")
        return True
    except Exception as e:
        logger.error(f"❌ Error registering user {member.name} ({member.id}): {e}",
                     user_id=str(member.id),
                     guild_id=str(guild.id),
                     username=member.name,
                     operation="single_user_registration",
                     error_type=type(e).__name__)
        return None


def register_user_history(user_id: int, guild_id: int, user_name: str, topic_id: str, correct: int, total: int, types: List[str]):
    try:
        user_doc_ref = db.collection("servers") \
                         .document(str(guild_id)) \
                         .collection("users") \
                         .document(str(user_id))

        now_utc = datetime.now(tz=pytz.UTC)

        user_doc_ref.update({
            "history": firestore.ArrayUnion([{
                "date": now_utc,
                "failures": total - correct,
                "success": correct,
                "type": types,
                "topic_id": topic_id
            }])
        })

        logger.info(f"📌 History entry added for user {user_name} ({user_id})",
                    user_id=str(user_id),
                    guild_id=str(guild_id),
                    username=user_name,
                    topic_id=topic_id,
                    score=correct,
                    total_questions=total,
                    operation="quiz_history_update")
    except Exception as e:
        logger.error(f"❌ Error adding history entry for user {user_name} ({user_id}): {e}",
                     user_id=str(user_id),
                     guild_id=str(guild_id),
                     username=user_name,
                     topic_id=topic_id,
                     operation="quiz_history_update",
                     error_type=type(e).__name__)
