from firebase_init import db, SERVER_TIMESTAMP

def listar_topicos(guild_id):
    return db.collection("servers") \
             .document(str(guild_id)) \
             .collection("topics") \
             .get()

def criar_topico_com_perguntas(guild_id, topico, preguntas_novas, document_name, document_url):
    topic_ref = db.collection("servers").document(str(guild_id)).collection("topics").document()
    topic_id = topic_ref.id
    
    topic_data = {
        "title": topico,
        "created_at": SERVER_TIMESTAMP,
        "document_name": document_name,
        "document_storage_url": document_url,
        "num_quizzes_generated": len(preguntas_novas)
    }
    topic_ref.set(topic_data)

    batch = db.batch()
    for idx, pregunta in enumerate(preguntas_novas):
        pregunta_id = str(idx + 1)
        doc_ref = topic_ref.collection("questions").document(pregunta_id)
        batch.set(doc_ref, {
            "pregunta": pregunta.get("pregunta", ""),
            "respuesta": pregunta.get("respuesta", "V")
        })
    batch.commit()
    return topic_id

def obter_topics_por_servidor(guild_id: int):
    """
    Retorna todos os documentos da subcoleção 'topics' para um servidor específico.
    """
    try:
        return db.collection("servers") \
                 .document(str(guild_id)) \
                 .collection("topics") \
                 .get()
    except Exception as e:
        print(f"Erro ao obter tópicos para o servidor {guild_id}: {e}")
        return []

def obter_topics_para_autocompletar(guild_id: int):
    documentos = obter_topics_por_servidor(guild_id)
    return [doc.to_dict().get("title", "Sem título") for doc in documentos]

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

