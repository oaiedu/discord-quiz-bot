import logging
from firebase_init import db, Increment

def listar_perguntas_por_topico(guild_id: int, topic: str):
    try:
        topic_ref = db.collection("servers") \
                      .document(str(guild_id)) \
                      .collection("topics") \
                      .where("title", "==", topic) \
                      .limit(1) \
                      .get()

        if not topic_ref:
            return []

        perguntas_ref = topic_ref[0].reference.collection("questions").order_by("pregunta").get()
        return [doc.to_dict() | {"id": doc.id} for doc in perguntas_ref]

    except Exception as e:
        logging.error(f"Erro ao listar perguntas do tópico '{topic}' no servidor {guild_id}: {e}")
        return []


def adicionar_pergunta(guild_id: int, topic: str, pergunta: str, resposta: str):
    try:
        topic_ref = db.collection("servers") \
                      .document(str(guild_id)) \
                      .collection("topics") \
                      .where("title", "==", topic) \
                      .limit(1) \
                      .get()

        if not topic_ref:
            raise ValueError(f"Tópico '{topic}' não encontrado")

        questions_ref = topic_ref[0].reference.collection("questions")

        nova_ref = questions_ref.document()
        nova_ref.set({
            "pregunta": pergunta,
            "respuesta": resposta
        })
        return nova_ref.id

    except Exception as e:
        logging.error(f"Erro ao adicionar pergunta no tópico '{topic}' do servidor {guild_id}: {e}")
        raise  # relança o erro para ser tratado externamente se quiser


def deletar_pergunta(guild_id: int, topic: str, question_id: str):
    try:
        topic_ref = db.collection("servers") \
                      .document(str(guild_id)) \
                      .collection("topics") \
                      .where("title", "==", topic) \
                      .limit(1) \
                      .get()

        if not topic_ref:
            raise ValueError("Tópico não encontrado")

        pergunta_ref = topic_ref[0].reference.collection("questions").document(question_id)
        pergunta_ref.delete()

    except Exception as e:
        logging.error(f"Erro ao deletar pergunta {question_id} do tópico '{topic}' no servidor {guild_id}: {e}")
        raise  # relança o erro para ser tratado externamente se quiser


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
        logging.error(f"Erro ao atualizar estatísticas da pergunta {question_id} do tópico {topic_id} no servidor {guild_id}: {e}")
        raise
