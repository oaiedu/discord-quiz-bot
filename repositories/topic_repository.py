import logging
from firebase_init import db, bucket, SERVER_TIMESTAMP


def list_topics(guild_id):
    try:
        return db.collection("servers") \
                 .document(str(guild_id)) \
                 .collection("topics") \
                 .get()
    except Exception as e:
        logging.error(f"Error listing topics for server {guild_id}: {e}")
        return []


def create_topic_with_questions(guild_id, topic_title, topic_id, new_questions, document_url, qty, qtype):
    try:
        use_topic_id = None
        topic_ref = None

        if topic_id is None:
            topic_ref = db.collection("servers").document(
                str(guild_id)).collection("topics").document()
            new_topic_id = topic_ref.id
            use_topic_id = new_topic_id

            topic_data = {
                "title": topic_title,
                "created_at": SERVER_TIMESTAMP,
                "document_storage_url": document_url,
                "num_quizzes_generated": len(new_questions),
                "topic_id": new_topic_id
            }
            topic_ref.set(topic_data)
        else:
            topic_ref = db.collection("servers").document(
                str(guild_id)).collection("topics").document(str(topic_id))
            use_topic_id = topic_ref.id

        batch = db.batch()
        for idx, question in enumerate(new_questions):
            doc_ref = topic_ref.collection("questions").document()
            question_id = doc_ref.id
            batch.set(doc_ref, {
                "question_id": question_id,
                "question": question.get("question"),
                "alternatives": question.get("alternatives", ""),
                "correct_answer": question.get("answer"),
                "question_type": qtype.value,
                "success": 0,
                "failures": 0
            })
        batch.commit()
        logging.info(
            f"Topic '{topic_title}' with questions created/updated in server {guild_id} (ID: {use_topic_id})")
        return use_topic_id

    except Exception as e:
        logging.error(
            f"Error creating topic with questions in server {guild_id}: {e}")
        return None


def create_topic_without_questions(guild_id, topic_title, document_url):
    try:
        topic_ref = db.collection("servers").document(
            str(guild_id)).collection("topics").document()
        topic_id = topic_ref.id

        topic_data = {
            "title": topic_title,
            "created_at": SERVER_TIMESTAMP,
            "document_storage_url": document_url,
            "num_quizzes_generated": 0,
            "topic_id": topic_id
        }
        topic_ref.set(topic_data)
        logging.info(
            f"Topic '{topic_title}' created without questions in server {guild_id} (ID: {topic_id})")
        return topic_id

    except Exception as e:
        logging.error(
            f"Error creating topic without questions in server {guild_id}: {e}")
        return None


def get_topics_by_server(guild_id: int):
    try:
        return db.collection("servers") \
                 .document(str(guild_id)) \
                 .collection("topics") \
                 .get()
    except Exception as e:
        logging.error(f"Error getting topics for server {guild_id}: {e}")
        return []


def get_questions_by_topic(guild_id: int, topic_title: str):
    try:
        topic_collection = db.collection("servers") \
            .document(str(guild_id)) \
            .collection("topics")

        documents = topic_collection.where(
            "title", "==", topic_title).limit(1).get()

        if not documents:
            return []

        topic_doc = documents[0]
        return topic_doc.reference.collection("questions").get()

    except Exception as e:
        logging.error(
            f"Error getting questions for topic '{topic_title}': {e}")
        return []


def get_topic_by_name(guild_id: int, topic_name: str):
    try:
        topic_collection = db.collection("servers") \
            .document(str(guild_id)) \
            .collection("topics")

        document = topic_collection.where(
            "title", "==", topic_name).limit(1).get()

        if not document:
            return None

        topic_doc = document[0]
        return topic_doc.to_dict()
    except Exception as e:
        logging.error(f"Error getting topic '{topic_name}': {e}")
        return None


def save_topic_pdf(pdf_path, guild_id):
    try:
        topic_ref = db.collection("servers").document(
            str(guild_id)).collection("topics").document()
        topic_id = topic_ref.id

        storage_filename = f"{topic_id}.pdf"
        blob = bucket.blob(f"{guild_id}/topics/{storage_filename}")

        with open(pdf_path, "rb") as f:
            blob.upload_from_file(f, content_type="application/pdf")
            blob.make_public()

        document_url = blob.public_url
        logging.info(
            f"PDF saved to bucket for server {guild_id}, topic {topic_id}")
        return document_url
    except Exception as e:
        logging.error(f"Error saving topic PDF for server {guild_id}: {e}")
        return None
