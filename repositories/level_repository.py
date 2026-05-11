import logging
from firebase_init import db, Increment
from firebase_admin import firestore
from utils.structured_logging import structured_logger as logger


def add_xp(user_id: str, guild_id: str, xp_change: int):
    try:
        user_ref = db.collection("servers").document(
            guild_id).collection("users").document(user_id)
        user_data = user_ref.get().to_dict() or {}

        current_xp = user_data.get("xp", 0)
        new_xp = max(0, current_xp + xp_change)

        user_ref.set({
            "xp": new_xp,
            "level": calculate_level(new_xp)
        }, merge=True)

        logger.info(
            f"✅ XP updated for user {user_id} in guild {guild_id}",
            operation="add_xp",
            user_id=user_id,
            guild_id=guild_id,
            xp_change=xp_change,
            new_xp=new_xp
        )

        return new_xp
    except Exception as e:
        logger.error(
            f"❌ Error in add_xp: {e}",
            operation="add_xp",
            user_id=user_id,
            guild_id=guild_id,
            xp_change=xp_change
        )
        return 0


def get_user_xp(user_id: str, guild_id: str):
    try:
        user_ref = db.collection("servers").document(
            guild_id).collection("users").document(user_id)
        data = user_ref.get().to_dict()
        if data:
            xp, level = data.get("xp", 0), data.get("level", 1)
        else:
            xp, level = 0, 1

        logger.debug(
            f"📊 Retrieved XP for user {user_id} in guild {guild_id}",
            operation="get_user_xp",
            user_id=user_id,
            guild_id=guild_id,
            xp=xp,
            level=level
        )

        return xp, level
    except Exception as e:
        logger.error(
            f"❌ Error in get_user_xp: {e}",
            operation="get_user_xp",
            user_id=user_id,
            guild_id=guild_id
        )
        return 0, 1


def get_user_xp_by_name(user_name: str, guild_id: str):
    try:
        user_docs = (
            db.collection("servers").document(guild_id).collection("users")
            .where("name", "==", user_name)
            .limit(1)
            .get()
        )

        if not user_docs:
            logger.warning(
                f"⚠️ User not found by name {user_name} in guild {guild_id}",
                operation="get_user_xp_by_name",
                user_name=user_name,
                guild_id=guild_id
            )
            return 0, 1

        data = user_docs[0].to_dict()
        xp, level = data.get("xp", 0), data.get("level", 1)

        logger.debug(
            f"📊 Retrieved XP by name for {user_name} in guild {guild_id}",
            operation="get_user_xp_by_name",
            user_name=user_name,
            guild_id=guild_id,
            xp=xp,
            level=level
        )

        return xp, level
    except Exception as e:
        logger.error(
            f"❌ Error in get_user_xp_by_name: {e}",
            operation="get_user_xp_by_name",
            user_name=user_name,
            guild_id=guild_id
        )
        return 0, 1


def get_leaderboard(guild_id: str, limit: int = 10):
    try:
        users = (
            db.collection("servers")
            .document(guild_id)
            .collection("users")
            .order_by("xp", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        leaderboard = [(u.id, u.to_dict().get("xp", 0),
                        u.to_dict().get("level", 1)) for u in users]

        logger.info(
            f"🏆 Leaderboard retrieved for guild {guild_id}",
            operation="get_leaderboard",
            guild_id=guild_id,
            limit=limit,
            leaderboard_size=len(leaderboard)
        )

        return leaderboard
    except Exception as e:
        logger.error(
            f"❌ Error in get_leaderboard: {e}",
            operation="get_leaderboard",
            guild_id=guild_id,
            limit=limit
        )
        return []


def calculate_level(xp: int) -> int:
    return xp // 100 + 1
    # OR exponential curve:
    # level = int((xp / 50) ** 0.5) + 1


def update_streak(user_id, guild_id, is_correct):
    try:
        user_ref = db.collection("servers").document(
            guild_id).collection("users").document(user_id)
        user_data = user_ref.get().to_dict() or {}
        streak = user_data.get("streak", 0)

        if is_correct:
            streak += 1
        else:
            streak = 0

        user_ref.set({"streak": streak}, merge=True)

        logger.info(
            f"🔥 Streak updated for user {user_id} in guild {guild_id}",
            operation="update_streak",
            user_id=user_id,
            guild_id=guild_id,
            is_correct=is_correct,
            new_streak=streak
        )

        return streak
    except Exception as e:
        logger.error(
            f"❌ Error in update_streak: {e}",
            operation="update_streak",
            user_id=user_id,
            guild_id=guild_id,
            is_correct=is_correct
        )
        return 0
