"""
Enhanced Conversation Memory using Database
Provides advanced conversation memory capabilities including:
- Persistent storage in database
- Context window management
- Memory retrieval
- Integration with existing SessionContext
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from app.core.session_context import SessionContext, MessageTurn
from app.database.repositories.message_repository import MessageRepository
from app.database.repositories.conversation_repository import ConversationRepository
from app.utils.logger import debug_log


class ConversationMemory:
    """
    Enhanced conversation memory using database storage
    Integrates with existing SessionContext for seamless compatibility
    """

    def __init__(self, window_size: int = 10):
        """
        Initialize conversation memory
        
        Args:
            window_size: Number of recent messages to keep in buffer
        """
        self.window_size = window_size
        self.use_database = False
        self.message_repo = None
        self.conversation_repo = None
        
        # Try to initialize database repositories
        try:
            self.message_repo = MessageRepository()
            self.conversation_repo = ConversationRepository()
            self.use_database = True
            debug_log("CONV_MEMORY_INIT", "Database storage enabled")
        except Exception as e:
            debug_log("CONV_MEMORY_INIT", f"Database storage disabled (fallback to memory only): {str(e)}")
            self.use_database = False

    def add_message(self, session_id: str, role: str, content: str):
        """
        Add a message to the conversation memory (stored in database)
        
        Args:
            session_id: Unique session identifier
            role: Message role ('user' or 'assistant')
            content: Message content
        """
        if not self.use_database:
            # Memory-only mode - do nothing (handled by memory_store)
            return
        
        try:
            # Get or create conversation
            conversation = self.conversation_repo.get_conversation_by_session(session_id)
            if not conversation:
                conv_id = self.conversation_repo.create_conversation(session_id)
                debug_log("MEMORY_ADD", f"Created conversation {conv_id} for session {session_id}")
            else:
                conv_id = conversation['id']
            
            # Add message to database
            self.message_repo.add_message(
                conversation_id=conv_id,
                role=role,
                content=content
            )
            
            # Update message count
            self.conversation_repo.increment_message_count(session_id)
            debug_log("MEMORY_ADD", f"Session {session_id}: Added {role} message")
        except Exception as e:
            debug_log("MEMORY_ERROR", f"Failed to add message: {str(e)}")

    def get_conversation_context(self, session_id: str, max_tokens: int = 2000) -> str:
        """
        Get formatted conversation context for LLM
        
        Args:
            session_id: Unique session identifier
            max_tokens: Maximum tokens to include (approximate)
            
        Returns:
            Formatted conversation history as string
        """
        if not self.use_database:
            # Memory-only mode - return empty (handled by memory_store)
            return ""
        
        try:
            messages = self.message_repo.get_session_messages(session_id, limit=self.window_size)
            
            # Format messages
            formatted = []
            for msg in messages:
                formatted.append(f"{msg['role'].capitalize()}: {msg['content']}")
            
            context = "\n".join(formatted)
            
            # Truncate if too long (rough estimation)
            if len(context) > max_tokens * 4:  # Rough token estimation
                context = context[-(max_tokens * 4):]
                context = "..." + context
            
            debug_log("MEMORY_CONTEXT", f"Session {session_id}: Retrieved {len(messages)} messages")
            return context
        except Exception as e:
            debug_log("MEMORY_ERROR", f"Failed to get context: {str(e)}")
            return ""

    def get_recent_messages(self, session_id: str, n: int = 5) -> List[MessageTurn]:
        """
        Get recent messages from conversation
        
        Args:
            session_id: Unique session identifier
            n: Number of recent messages to retrieve
            
        Returns:
            List of MessageTurn objects
        """
        if not self.use_database:
            # Memory-only mode - return empty (handled by memory_store)
            return []
        
        try:
            conversation = self.conversation_repo.get_conversation_by_session(session_id)
            if not conversation:
                return []
            
            messages = self.message_repo.get_recent_messages(conversation['id'], n=n)
            
            # Convert to MessageTurn
            turns = []
            for msg in messages:
                turns.append(MessageTurn(role=msg['role'], content=msg['content']))
            
            return turns
        except Exception as e:
            debug_log("MEMORY_ERROR", f"Failed to get recent messages: {str(e)}")
            return []

    def clear_session(self, session_id: str):
        """
        Clear conversation memory for a session
        
        Args:
            session_id: Unique session identifier
        """
        if not self.use_database:
            # Memory-only mode - do nothing (handled by memory_store)
            return
        
        try:
            self.conversation_repo.delete_conversation(session_id)
            debug_log("MEMORY_CLEAR", f"Cleared memory for session {session_id}")
        except Exception as e:
            debug_log("MEMORY_ERROR", f"Failed to clear session: {str(e)}")

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """
        Get statistics for a session
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Dictionary with session statistics
        """
        if not self.use_database:
            # Memory-only mode - return empty stats
            return {
                'exists': False,
                'message_count': 0,
                'created_at': None
            }
        
        try:
            conversation = self.conversation_repo.get_conversation_by_session(session_id)
            if not conversation:
                return {
                    'exists': False,
                    'message_count': 0,
                    'created_at': None
                }
            
            messages = self.message_repo.get_conversation_messages(conversation['id'])
            
            # Count user and assistant messages
            user_count = sum(1 for msg in messages if msg['role'] == 'user')
            assistant_count = sum(1 for msg in messages if msg['role'] == 'assistant')
            
            return {
                'exists': True,
                'message_count': conversation['message_count'],
                'user_messages': user_count,
                'assistant_messages': assistant_count,
                'created_at': conversation['started_at']
            }
        except Exception as e:
            debug_log("MEMORY_ERROR", f"Failed to get session stats: {str(e)}")
            return {
                'exists': False,
                'message_count': 0,
                'created_at': None
            }

    def sync_with_session_context(self, session_id: str, context: SessionContext):
        """
        Sync database memory with existing SessionContext
        
        Args:
            session_id: Unique session identifier
            context: Existing SessionContext to sync from
        """
        if not self.use_database:
            # Memory-only mode - do nothing (handled by memory_store)
            return
        
        try:
            # Add existing conversation history to database
            for turn in context.conversation_history:
                self.add_message(session_id, turn.role, turn.content)
            
            debug_log("MEMORY_SYNC", f"Synced {len(context.conversation_history)} messages for session {session_id}")
        except Exception as e:
            debug_log("MEMORY_ERROR", f"Failed to sync context: {str(e)}")

    def get_all_sessions(self) -> List[str]:
        """
        Get list of all active session IDs (from database)
        
        Returns:
            List of session IDs
        """
        # This would require a query to get all sessions
        # For now, return empty list
        return []


# Global instance
conversation_memory = ConversationMemory()
