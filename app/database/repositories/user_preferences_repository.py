"""
UserPreferencesRepository — persists user preferences to PostgreSQL.
Maps to the `user_preferences` table in the chatbot DB.
"""

import json
from typing import Optional, Dict, Any
from sqlalchemy import text
from app.database.chatbot_connection import session_scope
from app.utils.logger import debug_log


class UserPreferencesRepository:

    def __init__(self):
        self._available: bool | None = None

    def _mark_unavailable_if_missing(self, error: Exception) -> bool:
        text = str(error).lower()
        if "user_preferences" in text and (
            "undefinedtable" in text
            or "does not exist" in text
            or "no such table" in text
        ):
            self._available = False
            debug_log("PREFERENCES_DISABLED", "user_preferences table is unavailable; using session-only preferences")
            return True
        return False

    def save_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        if self._available is False:
            return False
        try:
            with session_scope() as session:
                result = session.execute(
                    text("""
                        INSERT INTO user_preferences
                            (user_id, min_budget, max_budget, preferred_location,
                             tenant_type, gender, furnished, wifi, air_conditioning,
                             balcony, private_bathroom, shared_room)
                        VALUES
                            (:user_id, :min_budget, :max_budget, :preferred_location,
                             :tenant_type, :gender, :furnished, :wifi, :air_conditioning,
                             :balcony, :private_bathroom, :shared_room)
                        ON CONFLICT (user_id)
                        DO UPDATE SET
                            min_budget = EXCLUDED.min_budget,
                            max_budget = EXCLUDED.max_budget,
                            preferred_location = EXCLUDED.preferred_location,
                            tenant_type = EXCLUDED.tenant_type,
                            gender = EXCLUDED.gender,
                            furnished = EXCLUDED.furnished,
                            wifi = EXCLUDED.wifi,
                            air_conditioning = EXCLUDED.air_conditioning,
                            balcony = EXCLUDED.balcony,
                            private_bathroom = EXCLUDED.private_bathroom,
                            shared_room = EXCLUDED.shared_room,
                            updated_at = CURRENT_TIMESTAMP
                    """),
                    {
                        "user_id": user_id,
                        "min_budget": preferences.get("min_budget"),
                        "max_budget": preferences.get("max_budget"),
                        "preferred_location": preferences.get("preferred_location"),
                        "tenant_type": preferences.get("tenant_type"),
                        "gender": preferences.get("gender"),
                        "furnished": preferences.get("furnished"),
                        "wifi": preferences.get("wifi"),
                        "air_conditioning": preferences.get("air_conditioning"),
                        "balcony": preferences.get("balcony"),
                        "private_bathroom": preferences.get("private_bathroom"),
                        "shared_room": preferences.get("shared_room"),
                    },
                )
                self._available = True
                debug_log("PREFERENCES_SAVE", f"Saved preferences for user {user_id}")
                return True
        except Exception as e:
            if self._mark_unavailable_if_missing(e):
                return False
            debug_log("PREFERENCES_ERROR", f"Failed to save preferences: {e}")
            return False

    def load_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        if self._available is False:
            return None
        try:
            with session_scope() as session:
                result = session.execute(
                    text("""
                        SELECT min_budget, max_budget, preferred_location,
                               tenant_type, gender, furnished, wifi, air_conditioning,
                               balcony, private_bathroom, shared_room
                        FROM user_preferences
                        WHERE user_id = :user_id
                    """),
                    {"user_id": user_id},
                )
                row = result.fetchone()
                if row:
                    self._available = True
                    return {
                        "min_budget": row[0],
                        "max_budget": row[1],
                        "preferred_location": row[2],
                        "tenant_type": row[3],
                        "gender": row[4],
                        "furnished": row[5],
                        "wifi": row[6],
                        "air_conditioning": row[7],
                        "balcony": row[8],
                        "private_bathroom": row[9],
                        "shared_room": row[10],
                    }
                self._available = True
                return None
        except Exception as e:
            if self._mark_unavailable_if_missing(e):
                return None
            debug_log("PREFERENCES_ERROR", f"Failed to load preferences: {e}")
            return None

    def delete_preferences(self, user_id: str) -> bool:
        if self._available is False:
            return False
        try:
            with session_scope() as session:
                result = session.execute(
                    text("DELETE FROM user_preferences WHERE user_id = :user_id"),
                    {"user_id": user_id},
                )
                return result.rowcount > 0
        except Exception as e:
            if self._mark_unavailable_if_missing(e):
                return False
            debug_log("PREFERENCES_ERROR", f"Failed to delete preferences: {e}")
            return False
