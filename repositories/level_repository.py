import logging
from firebase_init import db, Increment
from firebase_admin import firestore

def add_xp(user_id: str, guild_id: str, xp_change: int):
    user_ref = db.collection("servers").document(guild_id).collection("users").document(user_id)
    user_data = user_ref.get().to_dict() or {}

    current_xp = user_data.get("xp", 0)
    new_xp = max(0, current_xp + xp_change)

    user_ref.set({
        "xp": new_xp,
        "level": calculate_level(new_xp)
    }, merge=True)

    return new_xp

def get_user_xp(user_id: str, guild_id: str):
    user_ref = db.collection("servers").document(guild_id).collection("users").document(user_id)
    data = user_ref.get().to_dict()
    if data:
        return data.get("xp", 0), data.get("level", 1)
    return 0, 1

def get_leaderboard(guild_id: str, limit: int = 10):
    users = db.collection("servers").document(guild_id).collection("users").order_by("xp", direction=firestore.Query.DESCENDING).limit(limit).stream()
    return [(u.id, u.to_dict().get("xp", 0), u.to_dict().get("level", 1)) for u in users]

def calculate_level(xp: int) -> int:
    # Linear: 100 XP por nível
    return xp // 100 + 1
    # OU curva exponencial:
    # level = int((xp / 50) ** 0.5) + 1
    
def update_streak(user_id, guild_id, is_correct):
    user_ref = db.collection("servers").document(guild_id).collection("users").document(user_id)
    user_data = user_ref.get().to_dict() or {}
    streak = user_data.get("streak", 0)

    if is_correct:
        streak += 1
    else:
        streak = 0

    user_ref.set({"streak": streak}, merge=True)
    return streak