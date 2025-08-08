from firebase_init import db, SERVER_TIMESTAMP
import logging

def guardar_estadistica(guild_id, usuario, topico, correctas, total):
    try:
        db.collection("servers").document(str(guild_id)).collection("stats").add({
            "usuario_id": str(usuario.id),
            "nombre": usuario.name,
            "tema": topico,
            "correctas": correctas,
            "total": total,
            "timestamp": SERVER_TIMESTAMP
        })
        logging.info(f"✅ Estatística guardada para usuário {usuario.id} no servidor {guild_id}")
    except Exception as e:
        logging.error(f"❌ Erro ao guardar estatística para usuário {usuario.id} no servidor {guild_id}: {e}")

def obter_estatisticas_por_servidor(guild_id: int):
    """
    Busca todos os usuários do servidor e retorna um dict com
    as estatísticas do campo 'history' de cada usuário.
    """
    try:
        users_docs = db.collection("servers") \
                       .document(str(guild_id)) \
                       .collection("users") \
                       .stream()

        datos = {}

        for user_doc in users_docs:
            user_data = user_doc.to_dict()
            user_name = user_data.get("name", "Sin nombre")
            history = user_data.get("history", [])
            
            if not history:
                continue
            
            uid = user_doc.id
            datos[uid] = {"nombre": user_name, "intentos": history}

        return datos

    except Exception as e:
        logging.error(f"❌ Erro ao obter estadísticas para o servidor {guild_id}: {e}")
        return {}
