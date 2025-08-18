from firebase_init import db
from datetime import datetime
from collections import defaultdict
import logging


def get_quizzes_by_period(guild_id: int):
    try:
        users_ref = db.collection("servers") \
                      .document(str(guild_id)) \
                      .collection("users")

        users_docs = users_ref.stream()

        quizzes_per_day = defaultdict(int)

        for doc in users_docs:
            data = doc.to_dict()
            history = data.get("history", [])

            for entry in history:
                quiz_date = entry.get("date")
                if isinstance(quiz_date, datetime):
                    date_str = quiz_date.date().isoformat()
                    quizzes_per_day[date_str] += 1

        ordered_quizzes = dict(sorted(quizzes_per_day.items()))
        return ordered_quizzes

    except Exception as e:
        logging.error(f"❌ Error while getting quizzes by period: {e}")
        return {}
