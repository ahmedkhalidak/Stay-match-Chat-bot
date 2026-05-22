"""
MemoryStore — بيحتفظ بالـ session context لكل مستخدم في الميموري
مع تخزين دايم في الداتابيز (conversations & messages)
Thread-safe باستخدام Lock
"""

from threading import Lock
from app.core.session_context import SessionContext
from app.utils.logger import debug_log


class MemoryStore:

    def __init__(self):
        self._store: dict[str, SessionContext] = {}
        self._lock = Lock()
        self.use_database = False
        self.conversation_repo = None
        self.message_repo = None
        
        # Try to initialize database repositories
        try:
            from app.database.repositories.conversation_repository import ConversationRepository
            from app.database.repositories.message_repository import MessageRepository
            self.conversation_repo = ConversationRepository()
            self.message_repo = MessageRepository()
            self.use_database = True
            debug_log("MEMORY_INIT", "Database storage enabled")
        except Exception as e:
            debug_log("MEMORY_INIT", f"Database storage disabled (fallback to memory only): {str(e)}")
            self.use_database = False

    def get_context(self, session_id: str) -> SessionContext:
        with self._lock:
            # Check if in memory
            if session_id not in self._store:
                if self.use_database:
                    # Try to load from database
                    try:
                        conversation = self.conversation_repo.get_conversation_by_session(session_id)
                        if conversation:
                            # Load messages from database
                            messages = self.message_repo.get_session_messages(session_id)
                            ctx = SessionContext()
                            for msg in messages:
                                ctx.add_message(msg['role'], msg['content'])
                            self._store[session_id] = ctx
                            debug_log("MEMORY_LOAD", f"Loaded conversation {conversation['id']} from database")
                            return self._store[session_id]
                    except Exception as e:
                        debug_log("MEMORY_ERROR", f"Failed to load from database: {str(e)}")
                
                # Create new session in memory (and database if enabled)
                self._store[session_id] = SessionContext()
                if self.use_database:
                    try:
                        conv_id = self.conversation_repo.create_conversation(session_id)
                        debug_log("MEMORY_CREATE", f"Created new conversation {conv_id} in database")
                    except Exception as e:
                        debug_log("MEMORY_ERROR", f"Failed to create in database: {str(e)}")
            
            return self._store[session_id]

    def update_context(self, session_id: str, context: SessionContext):
        with self._lock:
            self._store[session_id] = context
            # Update last activity in database
            if self.use_database:
                try:
                    self.conversation_repo.update_last_activity(session_id, len(context.conversation_history))
                except Exception as e:
                    debug_log("MEMORY_ERROR", f"Failed to update database: {str(e)}")

    def clear_context(self, session_id: str):
        """امسح السيشن — مفيد للـ testing أو reset"""
        with self._lock:
            self._store.pop(session_id, None)
            # Also delete from database
            if self.use_database:
                try:
                    self.conversation_repo.delete_conversation(session_id)
                    debug_log("MEMORY_CLEAR", f"Cleared session {session_id} from memory and database")
                except Exception as e:
                    debug_log("MEMORY_ERROR", f"Failed to delete from database: {str(e)}")

    def active_sessions(self) -> int:
        """عدد السيشنز النشطة — للـ monitoring"""
        with self._lock:
            return len(self._store)

    def add_message(self, session_id: str, role: str, content: str):
        """تسجيل رسالة في السيشن مع تخزين في الداتابيز"""
        ctx = self.get_context(session_id)
        ctx.add_message(role, content)
        self.update_context(session_id, ctx)
        
        # Store message in database
        if self.use_database:
            try:
                conversation = self.conversation_repo.get_conversation_by_session(session_id)
                if conversation:
                    self.message_repo.add_message(
                        conversation_id=conversation['id'],
                        role=role,
                        content=content
                    )
                    self.conversation_repo.increment_message_count(session_id)
                    debug_log("MEMORY_STORE", f"Stored message in database for session {session_id}")
            except Exception as e:
                debug_log("MEMORY_ERROR", f"Failed to store in database: {str(e)}")


memory_store = MemoryStore()
