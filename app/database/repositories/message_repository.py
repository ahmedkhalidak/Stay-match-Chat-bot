"""
Message Repository for Chatbot Database
Handles message storage and retrieval
"""

from typing import Optional, List, Dict, Any
from sqlalchemy import text
from app.database.chatbot_connection import get_chatbot_engine
from app.utils.logger import debug_log
from datetime import datetime


class MessageRepository:
    """Repository for messages table"""

    def __init__(self):
        self.engine = get_chatbot_engine()

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        message_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Add a message to a conversation
        
        Args:
            conversation_id: Conversation ID
            role: Message role (user, assistant, system)
            content: Message content
            message_type: Message type (text, image, file)
            metadata: Optional JSON metadata
            
        Returns:
            Message ID
        """
        try:
            import json
            metadata_json = json.dumps(metadata) if metadata else None
            
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        INSERT INTO messages (conversation_id, role, content, message_type, metadata)
                        VALUES (:conversation_id, :role, :content, :message_type, :metadata)
                        RETURNING id
                    """),
                    {
                        "conversation_id": conversation_id,
                        "role": role,
                        "content": content,
                        "message_type": message_type,
                        "metadata": metadata_json
                    }
                )
                conn.commit()
                message_id = result.scalar()
                debug_log("MESSAGE_ADD", f"Added message {message_id} to conversation {conversation_id}")
                return message_id
        except Exception as e:
            debug_log("MESSAGE_ERROR", f"Failed to add message: {str(e)}")
            raise

    def get_conversation_messages(
        self,
        conversation_id: int,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get all messages for a conversation
        
        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages to return
            
        Returns:
            List of messages
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT id, conversation_id, role, content, created_at, message_type, metadata
                        FROM messages
                        WHERE conversation_id = :conversation_id
                        ORDER BY created_at ASC
                        LIMIT :limit
                    """),
                    {"conversation_id": conversation_id, "limit": limit}
                )
                messages = []
                for row in result:
                    messages.append({
                        "id": row[0],
                        "conversation_id": row[1],
                        "role": row[2],
                        "content": row[3],
                        "created_at": row[4],
                        "message_type": row[5],
                        "metadata": row[6]
                    })
                return messages
        except Exception as e:
            debug_log("MESSAGE_ERROR", f"Failed to get messages: {str(e)}")
            return []

    def get_session_messages(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get all messages for a session (by session_id)
        
        Args:
            session_id: Session identifier
            limit: Maximum number of messages to return
            
        Returns:
            List of messages
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT m.id, m.conversation_id, m.role, m.content, m.created_at, m.message_type, m.metadata
                        FROM messages m
                        INNER JOIN conversations c ON m.conversation_id = c.id
                        WHERE c.session_id = :session_id
                        ORDER BY m.created_at ASC
                        LIMIT :limit
                    """),
                    {"session_id": session_id, "limit": limit}
                )
                messages = []
                for row in result:
                    messages.append({
                        "id": row[0],
                        "conversation_id": row[1],
                        "role": row[2],
                        "content": row[3],
                        "created_at": row[4],
                        "message_type": row[5],
                        "metadata": row[6]
                    })
                return messages
        except Exception as e:
            debug_log("MESSAGE_ERROR", f"Failed to get session messages: {str(e)}")
            return []

    def get_recent_messages(
        self,
        conversation_id: int,
        n: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get the most recent n messages for a conversation
        
        Args:
            conversation_id: Conversation ID
            n: Number of recent messages
            
        Returns:
            List of recent messages
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT id, conversation_id, role, content, created_at
                        FROM messages
                        WHERE conversation_id = :conversation_id
                        ORDER BY created_at DESC
                        LIMIT :n
                    """),
                    {"conversation_id": conversation_id, "n": n}
                )
                messages = []
                for row in result:
                    messages.append({
                        "id": row[0],
                        "conversation_id": row[1],
                        "role": row[2],
                        "content": row[3],
                        "created_at": row[4]
                    })
                # Reverse to get chronological order
                return list(reversed(messages))
        except Exception as e:
            debug_log("MESSAGE_ERROR", f"Failed to get recent messages: {str(e)}")
            return []

    def delete_conversation_messages(self, conversation_id: int) -> bool:
        """
        Delete all messages for a conversation
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("DELETE FROM messages WHERE conversation_id = :conversation_id"),
                    {"conversation_id": conversation_id}
                )
                conn.commit()
                deleted = result.rowcount > 0
                debug_log("MESSAGE_DELETE", f"Deleted {result.rowcount} messages for conversation {conversation_id}")
                return deleted
        except Exception as e:
            debug_log("MESSAGE_ERROR", f"Failed to delete messages: {str(e)}")
            return False
