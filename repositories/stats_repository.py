from firebase_init import db, SERVER_TIMESTAMP
from repositories.topic_repository import get_topic_by_name, get_questions_by_topic
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

def get_topic_statistics(guild_id: int, topic: str):
    try:
        topic_data = get_topic_by_name(guild_id, topic)
        if not topic_data:
            return None

        question_docs = get_questions_by_topic(guild_id, topic)
        questions = [doc.to_dict() for doc in question_docs] if question_docs else []

        normalized = []
        for q in questions:
            text = str(q.get("question", "Pregunta sin texto")).strip()
            success = int(q.get("success", 0) or 0)
            failures = int(q.get("failures", 0) or 0)
            normalized.append({
                "question": text,
                "success": success,
                "failures": failures
            })

        total_success = sum(q["success"] for q in normalized)
        total_failures = sum(q["failures"] for q in normalized)
        total_answers = total_success + total_failures
        accuracy = (total_success / total_answers * 100.0) if total_answers > 0 else 0.0

        top_success = sorted(
            normalized,
            key=lambda x: (x["success"], -x["failures"]),
            reverse=True
        )[:3]

        top_failures = sorted(
            normalized,
            key=lambda x: (x["failures"], -x["success"]),
            reverse=True
        )[:3]

        conclusion = (
            "El tópico no está bien comprendido."
            if accuracy < 50.0
            else "El tópico está comprendido."
        )

        return {
            "topic": topic_data.get("title", topic),
            "total_success": total_success,
            "total_failures": total_failures,
            "total_answers": total_answers,
            "accuracy": accuracy,
            "top_success_questions": top_success,
            "top_failure_questions": top_failures,
            "conclusion": conclusion
        }

    except Exception as e:
        logging.error(f"❌ Error fetching topic statistics for '{topic}' in server {guild_id}: {e}")
        return None