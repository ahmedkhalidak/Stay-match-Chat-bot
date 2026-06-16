"""
RecommendationClient — bridges the chatbot service with the recommendation service.
Shares the same Neon PostgreSQL database, so it reads recommendation scores directly.
Also sends interactions and triggers sync via HTTP when the recommendation service URL is configured.
"""
import logging
import os
import threading
from typing import Optional

from app.database.chatbot_connection import get_chatbot_session
from sqlalchemy import text

logger = logging.getLogger("staymatch.recommendation_client")

_REC_SERVICE_URL = os.environ.get("RECOMMENDATION_SERVICE_URL", "")
_PREFERENCES_SYNC_CONFIGURED = os.environ.get("ENABLE_PREFERENCES_SYNC", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
_SYNC_ENABLED = True  # Cache: becomes False after first non-200 response


def _get_rec_url() -> str:
    """Get recommendation service URL from config or env."""
    try:
        from app.core.config import Settings
        url = Settings().recommendation_service_url
        if url:
            return url
    except Exception:
        pass
    return _REC_SERVICE_URL


def get_recommendation_scores(user_id: str, property_ids: list[int]) -> dict[int, float]:
    """
    Read recommendation scores directly from shared PostgreSQL.
    Both services use the same Neon instance.
    """
    if not property_ids:
        return {}
    try:
        session = get_chatbot_session()
        ids_str = ",".join(str(i) for i in property_ids)
        rows = session.execute(
            text(f"""
                SELECT property_id, score
                FROM property_recommendations
                WHERE user_id = :uid AND property_id IN ({ids_str})
                ORDER BY rank ASC
            """),
            {"uid": user_id}
        ).mappings().all()
        return {r["property_id"]: r["score"] for r in rows}
    except Exception as e:
        logger.warning("Failed to read recommendation scores: %s", e)
        return {}


def get_room_recommendation_scores(user_id: str, room_ids: list[int]) -> dict[int, float]:
    """Read room recommendation scores from shared PostgreSQL."""
    if not room_ids:
        return {}
    try:
        session = get_chatbot_session()
        ids_str = ",".join(str(i) for i in room_ids)
        rows = session.execute(
            text(f"""
                SELECT room_id, score
                FROM room_recommendations
                WHERE user_id = :uid AND room_id IN ({ids_str})
                ORDER BY rank ASC
            """),
            {"uid": user_id}
        ).mappings().all()
        return {r["room_id"]: r["score"] for r in rows}
    except Exception as e:
        logger.warning("Failed to read room recommendation scores: %s", e)
        return {}


def _fire_and_forget(fn, *args, **kwargs):
    """Run a function in a background thread — never blocks the response."""
    threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True).start()


def trigger_recommendation_sync():
    """Call the recommendation service to trigger data sync from MSSQL."""
    url = _get_rec_url()
    if not url:
        logger.info("No recommendation service URL configured — skipping sync trigger")
        return False
    try:
        import httpx
        with httpx.Client(timeout=10) as client:
            resp = client.post(f"{url}/sync/refresh")
            if resp.status_code == 200:
                logger.info("Recommendation sync triggered successfully")
                return True
            else:
                logger.warning("Sync trigger returned status %s", resp.status_code)
                return False
    except Exception as e:
        logger.warning("Failed to trigger recommendation sync: %s", e)
        return False


def send_interaction(user_id: str, target_type: str, target_id: int, action: str,
                     dwell_seconds: Optional[int] = None,
                     search_lat: Optional[float] = None,
                     search_lng: Optional[float] = None):
    """
    Send user interaction to the recommendation service via HTTP (fire-and-forget).
    Falls back to direct DB insert if HTTP fails.
    """
    _fire_and_forget(_send_interaction_sync, user_id, target_type, target_id, action,
                     dwell_seconds, search_lat, search_lng)


def _send_interaction_sync(user_id: str, target_type: str, target_id: int, action: str,
                            dwell_seconds: Optional[int] = None,
                            search_lat: Optional[float] = None,
                            search_lng: Optional[float] = None):
    url = _get_rec_url()
    payload = {
        "user_id": user_id,
        "target_type": target_type,
        "target_id": target_id,
        "action": action,
    }
    if dwell_seconds is not None:
        payload["dwell_seconds"] = dwell_seconds
    if search_lat is not None:
        payload["search_lat"] = search_lat
    if search_lng is not None:
        payload["search_lng"] = search_lng

    if url:
        try:
            import httpx
            with httpx.Client(timeout=5) as client:
                resp = client.post(f"{url}/interactions", json=payload)
                if resp.status_code == 200:
                    return
                logger.warning("Interaction HTTP failed with status %s, falling back to DB", resp.status_code)
        except Exception as e:
            logger.warning("Interaction HTTP error: %s, falling back to DB", e)

    # Fallback: write directly to shared PostgreSQL
    try:
        session = get_chatbot_session()
        session.execute(
            text("""
                INSERT INTO user_interactions (user_id, target_type, target_id, action, dwell_seconds, search_lat, search_lng)
                VALUES (:user_id, :target_type, :target_id, :action, :dwell_seconds, :search_lat, :search_lng)
            """),
            payload
        )
        session.commit()
    except Exception as e:
        logger.warning("Failed to save interaction directly: %s", e)


def trigger_preferences_sync():
    """Sync chatbot user_preferences into recommendation service (fire-and-forget)."""
    if not _PREFERENCES_SYNC_CONFIGURED:
        return
    _fire_and_forget(_trigger_preferences_sync)


def _trigger_preferences_sync():
    global _SYNC_ENABLED
    if not _SYNC_ENABLED:
        return
    url = _get_rec_url()
    if not url:
        logger.info("No recommendation service URL — skipping preferences sync")
        return
    try:
        import httpx
        with httpx.Client(timeout=5) as client:
            resp = client.post(f"{url}/admin/sync-preferences")
            if resp.status_code == 200:
                logger.info("Preferences sync triggered")
            else:
                logger.warning("Preferences sync returned %s — disabling further sync calls", resp.status_code)
                _SYNC_ENABLED = False
    except Exception as e:
        logger.warning("Preferences sync failed: %s — disabling further sync calls", e)
        _SYNC_ENABLED = False
