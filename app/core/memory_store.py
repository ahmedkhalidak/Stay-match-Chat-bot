"""
MemoryStore — بيحتفظ بالـ session context لكل مستخدم في الميموري
Thread-safe باستخدام Lock
"""

from threading import Lock
from app.core.session_context import SessionContext


class MemoryStore:

    def __init__(self):
        self._store: dict[str, SessionContext] = {}
        self._lock = Lock()

    def get_context(self, session_id: str) -> SessionContext:
        with self._lock:
            if session_id not in self._store:
                self._store[session_id] = SessionContext()
            return self._store[session_id]

    def update_context(self, session_id: str, context: SessionContext):
        with self._lock:
            self._store[session_id] = context

    def clear_context(self, session_id: str):
        """امسح السيشن — مفيد للـ testing أو reset"""
        with self._lock:
            self._store.pop(session_id, None)

    def active_sessions(self) -> int:
        """عدد السيشنز النشطة — للـ monitoring"""
        with self._lock:
            return len(self._store)

    def add_message(self, session_id: str, role: str, content: str):
        """تسجيل رسالة في السيشن"""
        ctx = self.get_context(session_id)
        ctx.add_message(role, content)
        self.update_context(session_id, ctx)


memory_store = MemoryStore()
