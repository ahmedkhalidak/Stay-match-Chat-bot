"""
SearchHistoryRepository — persists search history to PostgreSQL.
Maps to the `search_history` table in the chatbot DB.
"""

import json
from typing import Optional, List, Dict, Any
from sqlalchemy import text
from app.database.chatbot_connection import get_chatbot_engine
from app.utils.logger import debug_log


class SearchHistoryRepository:

    def __init__(self):
        self.engine = get_chatbot_engine()

    def add_entry(
        self,
        session_id: str,
        search_type: str,
        results_count: int,
        city: Optional[str] = None,
        governorate: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        try:
            filters_json = json.dumps(filters) if filters else None
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        INSERT INTO search_history
                            (session_id, search_type, city, governorate,
                             min_price, max_price, results_count, filters)
                        VALUES
                            (:session_id, :search_type, :city, :governorate,
                             :min_price, :max_price, :results_count, :filters)
                        RETURNING id
                    """),
                    {
                        "session_id": session_id,
                        "search_type": search_type,
                        "city": city,
                        "governorate": governorate,
                        "min_price": min_price,
                        "max_price": max_price,
                        "results_count": results_count,
                        "filters": filters_json,
                    },
                )
                conn.commit()
                entry_id = result.scalar()
                debug_log("SEARCH_HISTORY_ADD", f"Entry {entry_id} for session {session_id}")
                return entry_id
        except Exception as e:
            debug_log("SEARCH_HISTORY_ERROR", f"Failed to add entry: {e}")
            return -1

    def get_session_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT id, session_id, search_type, city, governorate,
                               min_price, max_price, results_count, created_at, filters
                        FROM search_history
                        WHERE session_id = :session_id
                        ORDER BY created_at ASC
                        LIMIT :limit
                    """),
                    {"session_id": session_id, "limit": limit},
                )
                entries = []
                for row in result:
                    entries.append({
                        "id": row[0],
                        "session_id": row[1],
                        "search_type": row[2],
                        "city": row[3],
                        "governorate": row[4],
                        "min_price": row[5],
                        "max_price": row[6],
                        "results_count": row[7],
                        "created_at": row[8],
                        "filters": json.loads(row[9]) if row[9] else None,
                    })
                return entries
        except Exception as e:
            debug_log("SEARCH_HISTORY_ERROR", f"Failed to get history: {e}")
            return []

    def delete_session_history(self, session_id: str) -> bool:
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("DELETE FROM search_history WHERE session_id = :session_id"),
                    {"session_id": session_id},
                )
                conn.commit()
                return result.rowcount > 0
        except Exception as e:
            debug_log("SEARCH_HISTORY_ERROR", f"Failed to delete history: {e}")
            return False