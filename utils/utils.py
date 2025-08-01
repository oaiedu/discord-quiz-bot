from firebase_init import db, SERVER_TIMESTAMP
import logging
from datetime import datetime
import discord
from firebase_admin import firestore

def actualizar_ultima_interaccion(guild_id: int):
    try:
        db.collection("servers").document(str(guild_id)).update({
            "last_interaction": SERVER_TIMESTAMP
        })
        logging.info(f"🕒 Última interacción actualizada para servidor {guild_id}")
    except Exception as e:
        logging.error(f"❌ Error al actualizar la última interacción: {e}")

def registrar_user_estadistica(user: discord.User, topic_id: str, aciertos: int, total: int):
    try:
        user_doc_ref = db.collection("servers") \
                         .document(str(user.guild.id)) \
                         .collection("users") \
                         .document(str(user.id))

        user_doc_ref.update({
            "history": firestore.ArrayUnion([{
                "date": SERVER_TIMESTAMP,
                "failures": total - aciertos,
                "success": aciertos,
                "type": "true_false_quiz",
                "topic_id": topic_id
            }])
        })

        logging.info(f"📌 Histórico adicionado no array para o usuário {user.name} ({user.id})")
    except Exception as e:
        logging.error(f"❌ Erro ao adicionar histórico no array: {e}")   
