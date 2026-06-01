"""
ConversationMemory — now delegates to the consolidated MemoryStore.
Kept as thin wrapper for backward compatibility.
"""

from app.core.memory_store import memory_store
from app.core.session_context import MessageTurn
from app.utils.logger import debug_log


class ConversationMemory:

    def __init__(self, window_size: int = 10):
        self.window_size = window_size

    def add_message(self, session_id: str, role: str, content: str):
        ctx = memory_store.get_context_sync(session_id)
        ctx.add_message(role, content)
        memory_store._store[session_id] = ctx

    def get_conversation_context(self, session_id: str, max_tokens: int = 2000) -> str:
        ctx = memory_store.get_context_sync(session_id)
        history = ctx.get_history_text()
        if history and len(history) > max_tokens * 4:
            history = "..." + history[-(max_tokens * 4):]
        return history

    def get_recent_messages(self, session_id: str, n: int = 5):
        ctx = memory_store.get_context_sync(session_id)
        return ctx.conversation_history[-n:]

    def clear_session(self, session_id: str):
        import asyncio
        try:
            asyncio.run(memory_store.clear_context(session_id))
        except RuntimeError:
            pass

    def sync_with_session_context(self, session_id: str, context):
        pass

    def get_all_sessions(self):
        return []


conversation_memory = ConversationMemory()