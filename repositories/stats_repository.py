from firebase_init import db, SERVER_TIMESTAMP
import logging


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


def get_statistics_by_server(guild_id: int):
    """
    Fetch all users from the server and return a dict with
    the statistics from the 'history' field of each user.
    """
    try:
        users_docs = db.collection("servers") \
                       .document(str(guild_id)) \
                       .collection("users") \
                       .stream()

        data = {}

        for user_doc in users_docs:
            user_data = user_doc.to_dict()
            user_name = user_data.get("name", "No name")
            history = user_data.get("history", [])

            if not history:
                continue

            uid = user_doc.id
            data[uid] = {"name": user_name, "attempts": history}

        return data

    except Exception as e:
        logging.error(
            f"❌ Error fetching statistics for server {guild_id}: {e}")
        return {}
