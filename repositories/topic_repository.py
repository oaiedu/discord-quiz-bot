from firebase_init import db, bucket, SERVER_TIMESTAMP

def listar_topicos(guild_id):
    return db.collection("servers") \
             .document(str(guild_id)) \
             .collection("topics") \
             .get()

def criar_topico_com_perguntas(guild_id, topico, topic_id, preguntas_novas, document_url):
    use_topic_id = None
    topic_ref = None
    
    if topic_id == None:
        topic_ref = db.collection("servers").document(str(guild_id)).collection("topics").document()
        new_topic_id = topic_ref.id
        use_topic_id = new_topic_id
        
        topic_data = {
            "title": topico,
            "created_at": SERVER_TIMESTAMP,
            "document_storage_url": document_url,
            "num_quizzes_generated": len(preguntas_novas),
            "topic_id": new_topic_id
        }
        topic_ref.set(topic_data)
    else:
        topic_ref = db.collection("servers").document(str(guild_id)).collection("topics").document(str(topic_id))
        use_topic_id = topic_ref.id

    batch = db.batch()
    for idx, pregunta in enumerate(preguntas_novas):
        doc_ref = topic_ref.collection("questions").document()
        pregunta_id = doc_ref.id
        batch.set(doc_ref, {
            "question_id": pregunta_id,
            "question": pregunta.get("pregunta", ""),
            "correct_answer": pregunta.get("respuesta", "V"),
            "question_type": pregunta.get("question_type", "True or False"),
            "success": pregunta.get("success", 0),
            "failures": pregunta.get("failures", 0)
        })
    batch.commit()
    return use_topic_id

def criar_topico_sem_perguntas(guild_id, topico, document_url):
    topic_ref = db.collection("servers").document(str(guild_id)).collection("topics").document()
    topic_id = topic_ref.id
    
    topic_data = {
        "title": topico,
        "created_at": SERVER_TIMESTAMP,
        "document_storage_url": document_url,
        "num_quizzes_generated": 0,
        "topic_id": topic_id
    }
    topic_ref.set(topic_data)

    return topic_id

def obter_topics_por_servidor(guild_id: int):
    try:
        return db.collection("servers") \
                 .document(str(guild_id)) \
                 .collection("topics") \
                 .get()
    except Exception as e:
        print(f"Erro ao obter tópicos para o servidor {guild_id}: {e}")
        return []

def obter_preguntas_por_topic(guild_id: int, topic: str):
    try:
        colecao_topicos = db.collection("servers") \
                            .document(str(guild_id)) \
                            .collection("topics")

        documentos = colecao_topicos.where("title", "==", topic).limit(1).get()

        if not documentos:
            return []

        topic_doc = documentos[0]
        return topic_doc.reference.collection("questions").get()

    except Exception as e:
        print(f"Erro ao obter perguntas para o tópico '{topic}': {e}")
        return []

def get_topic_by_name(guild_id: int, topic_name: str):
    try:
        topic_collection = db.collection("servers") \
            .document(str(guild_id)) \
            .collection("topics")

        document = topic_collection.where("title", "==", topic_name).limit(1).get()

        if not document:
            return None

        topic_doc = document[0]
        return topic_doc.to_dict()  # Retorna todos os dados do documento como dict
    except Exception as e:
        print(f"Erro ao obter o tópico '{topic_name}': {e}")
        return None
    
def save_topic_pdf(ruta_pdf, guild_id):
    topic_ref = db.collection("servers").document(str(guild_id)).collection("topics").document()
    topic_id = topic_ref.id

    storage_filename = f"{topic_id}.pdf"
    blob = bucket.blob(f"{guild_id}/topics/{storage_filename}")

    with open(ruta_pdf, "rb") as f:
        blob.upload_from_file(f, content_type="application/pdf")
        blob.make_public()

    document_url = blob.public_url
    return document_url
