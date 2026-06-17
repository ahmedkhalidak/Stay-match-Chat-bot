"""
Conversation Repository for Chatbot Database
Handles conversation storage and retrieval
"""

from typing import Optional, List, Dict, Any
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database.chatbot_connection import session_scope
from app.utils.logger import debug_log
from datetime import datetime


class ConversationRepository:
    """Repository for conversations table"""

    def __init__(self):
        pass

    def create_conversation(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Create a new conversation, or return existing one if session_id already exists.
        
        Args:
            session_id: Unique session identifier
            user_id: Optional user identifier
            metadata: Optional JSON metadata
            
        Returns:
            Conversation ID
        """
        try:
            existing = self.get_conversation_by_session(session_id)
            if existing:
                debug_log("CONVERSATION_EXISTS", f"Session {session_id} already has conversation {existing['id']}")
                return existing["id"]

            import json
            metadata_json = json.dumps(metadata) if metadata else None
            
            with session_scope() as session:
                result = session.execute(
                    text("""
                        INSERT INTO conversations (session_id, user_id, metadata)
                        VALUES (:session_id, :user_id, :metadata)
                        RETURNING id
                    """),
                    {
                        "session_id": session_id,
                        "user_id": user_id,
                        "metadata": metadata_json
                    }
                )
                conversation_id = result.scalar()
                debug_log("CONVERSATION_CREATE", f"Created conversation {conversation_id} for session {session_id}")
                return conversation_id
        except Exception as e:
            debug_log("CONVERSATION_ERROR", f"Failed to create conversation: {str(e)}")
            raise

    def get_conversation_by_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get conversation by session ID
        
        Args:
            session_id: Session identifier
            
        Returns:
            Conversation data or None
        """
        try:
            with session_scope() as session:
                result = session.execute(
                    text("""
                        SELECT id, session_id, user_id, started_at, last_activity, 
                               message_count, status, metadata
                        FROM conversations
                        WHERE session_id = :session_id
                        ORDER BY id ASC
                        LIMIT 1
                    """),
                    {"session_id": session_id}
                )
                row = result.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "session_id": row[1],
                        "user_id": row[2],
                        "started_at": row[3],
                        "last_activity": row[4],
                        "message_count": row[5],
                        "status": row[6],
                        "metadata": row[7]
                    }
                return None
        except Exception as e:
            debug_log("CONVERSATION_ERROR", f"Failed to get conversation: {str(e)}")
            return None

    def update_last_activity(self, session_id: str, message_count: int = None):
        """
        Update last activity timestamp and optionally message count
        
        Args:
            session_id: Session identifier
            message_count: Optional new message count
        """
        try:
            with session_scope() as session:
                if message_count is not None:
                    session.execute(
                        text("""
                            UPDATE conversations
                            SET last_activity = CURRENT_TIMESTAMP,
                                message_count = :message_count
                            WHERE session_id = :session_id
                        """),
                        {"session_id": session_id, "message_count": message_count}
                    )
                else:
                    session.execute(
                        text("""
                            UPDATE conversations
                            SET last_activity = CURRENT_TIMESTAMP
                            WHERE session_id = :session_id
                        """),
                        {"session_id": session_id}
                    )
                debug_log("CONVERSATION_UPDATE", f"Updated activity for session {session_id}")
        except Exception as e:
            debug_log("CONVERSATION_ERROR", f"Failed to update conversation: {str(e)}")

    def update_user_id(self, session_id: str, user_id: str) -> bool:
        """Link a user_id to an existing conversation."""
        try:
            with session_scope() as session:
                session.execute(
                    text("""
                        UPDATE conversations
                        SET user_id = :user_id
                        WHERE session_id = :session_id
                    """),
                    {"session_id": session_id, "user_id": user_id},
                )
                debug_log("CONVERSATION_UPDATE", f"Linked user {user_id} to session {session_id}")
                return True
        except Exception as e:
            debug_log("CONVERSATION_ERROR", f"Failed to update user_id: {e}")
            return False

    def update_metadata(self, session_id: str, metadata: dict) -> bool:
        """Store/update JSON metadata for a conversation (full session context)."""
        try:
            import json
            meta_json = json.dumps(metadata)
            with session_scope() as session:
                session.execute(
                    text("""
                        UPDATE conversations
                        SET metadata = :metadata
                        WHERE session_id = :session_id
                    """),
                    {"session_id": session_id, "metadata": meta_json},
                )
                return True
        except Exception as e:
            debug_log("CONVERSATION_ERROR", f"Failed to update metadata: {e}")
            return False

    def increment_message_count(self, session_id: str):
        """
        Increment message count for a conversation
        
        Args:
            session_id: Session identifier
        """
        try:
            with session_scope() as session:
                session.execute(
                    text("""
                        UPDATE conversations
                        SET message_count = message_count + 1,
                            last_activity = CURRENT_TIMESTAMP
                        WHERE session_id = :session_id
                    """),
                    {"session_id": session_id}
                )
        except Exception as e:
            debug_log("CONVERSATION_ERROR", f"Failed to increment message count: {str(e)}")

    def delete_conversation(self, session_id: str) -> bool:
        """
        Delete a conversation (cascade deletes messages)
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            with session_scope() as session:
                result = session.execute(
                    text("DELETE FROM conversations WHERE session_id = :session_id"),
                    {"session_id": session_id}
                )
                deleted = result.rowcount > 0
                debug_log("CONVERSATION_DELETE", f"Deleted conversation for session {session_id}: {deleted}")
                return deleted
        except Exception as e:
            debug_log("CONVERSATION_ERROR", f"Failed to delete conversation: {str(e)}")
            return False

    def get_user_conversations(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get all conversations for a user
        
        Args:
            user_id: User identifier
            limit: Maximum number of conversations to return
            
        Returns:
            List of conversations
        """
        try:
            with session_scope() as session:
                result = session.execute(
                    text("""
                        SELECT id, session_id, user_id, started_at, last_activity,
                               message_count, status
                        FROM conversations
                        WHERE user_id = :user_id
                        ORDER BY last_activity DESC
                        LIMIT :limit
                    """),
                    {"user_id": user_id, "limit": limit}
                )
                conversations = []
                for row in result:
                    conversations.append({
                        "id": row[0],
                        "session_id": row[1],
                        "user_id": row[2],
                        "started_at": row[3],
                        "last_activity": row[4],
                        "message_count": row[5],
                        "status": row[6]
                    })
                return conversations
        except Exception as e:
            debug_log("CONVERSATION_ERROR", f"Failed to get user conversations: {str(e)}")
            return []
