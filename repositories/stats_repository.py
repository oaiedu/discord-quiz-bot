from firebase_init import db, SERVER_TIMESTAMP
import logging
from datetime import datetime


def save_statistic(guild_id, user, topic, correct, total):
    try:
        db.collection("servers").document(str(guild_id)).collection("stats").add({
            "user_id": str(user.id),
            "name": user.name,
            "topic": topic,
            "correct": correct,
            "total": total,
            "timestamp": SERVER_TIMESTAMP
        })
        logging.info(
            f"✅ Statistic saved for user {user.id} in server {guild_id}")
    except Exception as e:
        logging.error(
            f"❌ Error saving statistic for user {user.id} in server {guild_id}: {e}")


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_datetime(value):
    if hasattr(value, "to_datetime"):
        try:
            return value.to_datetime()
        except Exception:
            return None
    if isinstance(value, datetime):
        return value
    return None

def get_statistics_by_server(guild_id: int):
    """
    Mantiene el mismo contrato que ya usa stats_commands:
    {
        uid: {
            "name": str,
            "attempts": [
                {
                    "topic_id": str,
                    "success": int,
                    "failures": int,
                    "date": datetime | None
                }
            ]
        }
    }
    """
    try:
        docs = (
            db.collection("servers")
            .document(str(guild_id))
            .collection("stats")
            .stream()
        )

        data = {}

        for doc in docs:
            row = doc.to_dict() or {}

            uid = str(row.get("user_id") or "unknown")
            raw_name = str(row.get("name") or "").strip()
            display_name = raw_name if raw_name else f"User-{uid[-4:] if uid != 'unknown' else 'unk'}"

            correct = _safe_int(row.get("correct"), 0)
            total = max(_safe_int(row.get("total"), 0), 0)
            failures = max(total - correct, 0)
            topic_id = str(row.get("topic") or "Unknown")
            ts = _to_datetime(row.get("timestamp"))

            if uid not in data:
                data[uid] = {"name": display_name, "attempts": []}
            elif raw_name:
                data[uid]["name"] = raw_name

            data[uid]["attempts"].append({
                "topic_id": topic_id,
                "success": correct,
                "failures": failures,
                "date": ts
            })

        for info in data.values():
            info["attempts"].sort(key=lambda x: x.get("date") or datetime.min)

        return data

    except Exception as e:
        logging.error(f"❌ Error fetching statistics for server {guild_id}: {e}")
        return {}