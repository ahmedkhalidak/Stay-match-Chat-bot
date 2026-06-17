"""
SessionAnalyticsRepository — tracks session analytics in PostgreSQL.
Maps to the `session_analytics` table.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import text
from app.database.chatbot_connection import session_scope
from app.utils.logger import debug_log


class SessionAnalyticsRepository:

    def __init__(self):
        pass

    def create_session(self, session_id: str) -> bool:
        try:
            with session_scope() as session:
                session.execute(
                    text("""
                        INSERT INTO session_analytics (session_id)
                        VALUES (:session_id)
                        ON CONFLICT DO NOTHING
                    """),
                    {"session_id": session_id},
                )
                return True
        except Exception as e:
            debug_log("ANALYTICS_ERROR", f"Failed to create session: {e}")
            return False

    def increment_messages(self, session_id: str) -> bool:
        try:
            with session_scope() as session:
                session.execute(
                    text("""
                        UPDATE session_analytics
                        SET total_messages = total_messages + 1
                        WHERE session_id = :session_id
                    """),
                    {"session_id": session_id},
                )
                return True
        except Exception as e:
            debug_log("ANALYTICS_ERROR", f"Failed to increment messages: {e}")
            return False

    def increment_searches(self, session_id: str) -> bool:
        try:
            with session_scope() as session:
                session.execute(
                    text("""
                        UPDATE session_analytics
                        SET total_searches = total_searches + 1
                        WHERE session_id = :session_id
                    """),
                    {"session_id": session_id},
                )
                return True
        except Exception as e:
            debug_log("ANALYTICS_ERROR", f"Failed to increment searches: {e}")
            return False

    def increment_no_results(self, session_id: str) -> bool:
        try:
            with session_scope() as session:
                session.execute(
                    text("""
                        UPDATE session_analytics
                        SET no_results_count = no_results_count + 1
                        WHERE session_id = :session_id
                    """),
                    {"session_id": session_id},
                )
                return True
        except Exception as e:
            debug_log("ANALYTICS_ERROR", f"Failed to increment no_results: {e}")
            return False

    def end_session(self, session_id: str) -> bool:
        try:
            with session_scope() as session:
                session.execute(
                    text("""
                        UPDATE session_analytics
                        SET ended_at = CURRENT_TIMESTAMP
                        WHERE session_id = :session_id
                    """),
                    {"session_id": session_id},
                )
                return True
        except Exception as e:
            debug_log("ANALYTICS_ERROR", f"Failed to end session: {e}")
            return False

    def get_session_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        try:
            with session_scope() as session:
                result = session.execute(
                    text("""
                        SELECT total_messages, total_searches, no_results_count,
                               started_at, ended_at
                        FROM session_analytics
                        WHERE session_id = :session_id
                    """),
                    {"session_id": session_id},
                )
                row = result.fetchone()
                if row:
                    return {
                        "total_messages": row[0],
                        "total_searches": row[1],
                        "no_results_count": row[2],
                        "started_at": row[3],
                        "ended_at": row[4],
                    }
                return None
        except Exception as e:
            debug_log("ANALYTICS_ERROR", f"Failed to get stats: {e}")
            return None