from threading import Lock
from app.core.session_context import SessionContext


class MemoryStore:
    def __init__(self):
        self._store = {}
        self._lock = Lock()

    def get_context(self, session_id: str) -> SessionContext:
        with self._lock:
            if session_id not in self._store:
                self._store[session_id] = SessionContext()

            return self._store[session_id]

    def update_context(self, session_id: str, context: SessionContext):
        with self._lock:
            self._store[session_id] = context


memory_store = MemoryStore()