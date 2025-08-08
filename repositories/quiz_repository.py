from firebase_init import db
from datetime import datetime
from collections import defaultdict


def obter_quizzes_por_periodo(guild_id: int):
    try:
        usuarios_ref = db.collection("servers") \
                         .document(str(guild_id)) \
                         .collection("users")

        usuarios_docs = usuarios_ref.stream()

        quizzes_por_dia = defaultdict(int)

        for doc in usuarios_docs:
            dados = doc.to_dict()
            historico = dados.get("history", [])

            for entrada in historico:
                data_quiz = entrada.get("date")
                if isinstance(data_quiz, datetime):
                    data_str = data_quiz.date().isoformat()
                    quizzes_por_dia[data_str] += 1

        quizzes_ordenados = dict(sorted(quizzes_por_dia.items()))
        return quizzes_ordenados

    except Exception as e:
        import logging
        logging.error(f"❌ Erro ao obter quizzes por período: {e}")
        return {}