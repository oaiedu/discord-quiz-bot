from typing import List
from firebase_init import db, SERVER_TIMESTAMP
import logging
from firebase_admin import firestore
from datetime import datetime
import pytz

def registrar_usuarios_servidor(guild):
    try:
        batch = db.batch()
        for member in guild.members:
            if member.bot:
                continue
            doc_ref = db.collection("servers") \
                        .document(str(guild.id)) \
                        .collection("users") \
                        .document(str(member.id))
            batch.set(doc_ref, {
                "user_id": str(member.id),
                "name": member.name,
                "joined_bot_at": SERVER_TIMESTAMP
            })
        batch.commit()
        logging.info(f"✅ Usuários do servidor {guild.id} registrados com sucesso.")
    except Exception as e:
        logging.error(f"❌ Erro ao registrar usuários do servidor {guild.id}: {e}")

def register_single_user(guild, member):
    try:
        if member.bot:
            return None

        doc_ref = db.collection("servers") \
                    .document(str(guild.id)) \
                    .collection("users") \
                    .document(str(member.id))

        if doc_ref.get().exists:
            logging.info(f"⚠️ Usuário {member.name} ({member.id}) já está registrado.")
            return None

        doc_ref.set({
            "user_id": str(member.id),
            "name": member.name,
            "joined_bot_at": SERVER_TIMESTAMP
        })

        logging.info(f"✅ Usuário {member.name} ({member.id}) registrado com sucesso.")
        return True
    except Exception as e:
        logging.error(f"❌ Erro ao registrar usuário {member.name} ({member.id}): {e}")
        return None

def registrar_historico_usuario(user_id: int, guild_id: int, user_name: str, topic_id: str, acertos: int, total: int, types: List[str]):
    try:
        user_doc_ref = db.collection("servers") \
                         .document(str(guild_id)) \
                         .collection("users") \
                         .document(str(user_id))

        now_utc = datetime.now(tz=pytz.UTC)

        user_doc_ref.update({
            "history": firestore.ArrayUnion([{
                "date": now_utc,
                "failures": total - acertos,
                "success": acertos,
                "type": types,
                "topic_id": topic_id
            }])
        })

        logging.info(f"📌 Histórico adicionado no array para o usuário {user_name} ({user_id})")
    except Exception as e:
        logging.error(f"❌ Erro ao adicionar histórico no array para o usuário {user_name} ({user_id}): {e}")
