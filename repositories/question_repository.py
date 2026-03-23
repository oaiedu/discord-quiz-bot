import logging
from firebase_init import db, Increment


def _get_topic_ref_by_name(guild_id: int, topic: str):
    topic_ref = db.collection("servers") \
                  .document(str(guild_id)) \
                  .collection("topics") \
                  .where("title", "==", topic) \
                  .limit(1) \
                  .get()

    if not topic_ref:
        raise ValueError(f"Topic '{topic}' not found")

    return topic_ref[0].reference


def list_questions_by_topic(guild_id: int, topic: str):
    try:
        topic_ref = db.collection("servers") \
                      .document(str(guild_id)) \
                      .collection("topics") \
                      .where("title", "==", topic) \
                      .limit(1) \
                      .get()

        if not topic_ref:
            return []

        questions_ref = topic_ref[0].reference.collection("questions").get()
        questions = [{**doc.to_dict(), "id": doc.id} for doc in questions_ref]
        questions.sort(key=lambda q: q.get("question", ""))

        return questions

    except Exception as e:
        logging.error(f"Error listing questions for topic '{topic}' in server {guild_id}: {e}")
        return []


def add_question(guild_id: int, topic: str, question: str, answer: str):
    try:
        topic_doc_ref = _get_topic_ref_by_name(guild_id, topic)
        questions_ref = topic_doc_ref.collection("questions")

        new_ref = questions_ref.document()
        new_ref.set({
            "question": question,
            "correct_answer": answer
        })
        topic_doc_ref.update({
            "num_quizzes_generated": Increment(1)
        })
        return new_ref.id

    except Exception as e:
        logging.error(
            f"Error adding question to topic '{topic}' in server {guild_id}: {e}")
        raise  # re-raise the error for external handling if needed


def delete_question(guild_id: int, topic: str, question_id: str):
    try:
        topic_doc_ref = _get_topic_ref_by_name(guild_id, topic)
        question_ref = topic_doc_ref.collection("questions").document(question_id)

        if not question_ref.get().exists:
            raise ValueError(f"Question '{question_id}' not found")

        question_ref.delete()
        topic_doc_ref.update({
            "num_quizzes_generated": Increment(-1)
        })

    except Exception as e:
        logging.error(
            f"Error deleting question {question_id} from topic '{topic}' in server {guild_id}: {e}")
        raise  # re-raise the error for external handling if needed


def delete_all_questions_by_topic(guild_id: int, topic: str):
    try:
        topic_doc_ref = _get_topic_ref_by_name(guild_id, topic)
        question_docs = list(topic_doc_ref.collection("questions").stream())

        if not question_docs:
            return 0

        batch = db.batch()
        deleted_count = 0

        for index, question_doc in enumerate(question_docs, start=1):
            batch.delete(question_doc.reference)
            deleted_count += 1

            if index % 500 == 0:
                batch.commit()
                batch = db.batch()

        if deleted_count % 500 != 0:
            batch.commit()

        topic_doc_ref.update({
            "num_quizzes_generated": 0
        })

        return deleted_count

    except Exception as e:
        logging.error(
            f"Error deleting all questions from topic '{topic}' in server {guild_id}: {e}")
        raise


def update_question_stats(guild_id: int, topic_id: str, question_id: str, correct: bool):
    try:
        topic_ref = db.collection("servers") \
            .document(str(guild_id)) \
            .collection("topics") \
            .document(topic_id) \
            .collection("questions") \
            .document(question_id)

        if correct:
            topic_ref.update({
                "success": Increment(1)
            })
        else:
            topic_ref.update({
                "failures": Increment(1)
            })

    except Exception as e:
        logging.error(
            f"Error updating stats for question {question_id} in topic {topic_id} in server {guild_id}: {e}")
        raise
