"""
MemoryStore — consolidated single source of truth for session state.
Fully async, with fire-and-forget database persistence.
"""

import asyncio
import json
from typing import Optional

from app.core.session_context import SessionContext
from app.utils.logger import debug_log
from app.utils.language_detector import detect_language


class MemoryStore:

    def __init__(self):
        self._store: dict[str, SessionContext] = {}
        self._lock = asyncio.Lock()
        self.use_database = False
        self.conversation_repo = None
        self.message_repo = None
        self.search_history_repo = None
        self.preferences_repo = None
        self.analytics_repo = None
        self._max_sessions = 1000  # Limit in-memory sessions to prevent OOM

        try:
            from app.database.repositories.conversation_repository import ConversationRepository
            from app.database.repositories.message_repository import MessageRepository
            from app.database.repositories.search_history_repository import SearchHistoryRepository
            from app.database.repositories.user_preferences_repository import UserPreferencesRepository
            from app.database.repositories.session_analytics_repository import SessionAnalyticsRepository
            self.conversation_repo = ConversationRepository()
            self.message_repo = MessageRepository()
            self.search_history_repo = SearchHistoryRepository()
            self.preferences_repo = UserPreferencesRepository()
            self.analytics_repo = SessionAnalyticsRepository()
            self.use_database = True
        except Exception as e:
            debug_log("MEMORY_INIT", f"Database disabled: {e}")

    async def get_context(self, session_id: str, message: str = "") -> SessionContext:
        async with self._lock:
            if session_id in self._store:
                ctx = self._store[session_id]
                if message:
                    ctx.language = detect_language(message)
                return ctx

            # Not in memory — try to reconstruct from DB
            if self.use_database:
                try:
                    conversation = self.conversation_repo.get_conversation_by_session(session_id)
                    if conversation:
                        ctx = self._reconstruct_context(conversation, session_id)
                        if ctx:
                            if message:
                                ctx.language = detect_language(message)
                            self._store[session_id] = ctx
                            # Evict oldest sessions if limit exceeded
                            if len(self._store) > self._max_sessions:
                                oldest_key = next(iter(self._store))
                                del self._store[oldest_key]
                            return self._store[session_id]
                except Exception:
                    pass

            # Fresh session: create in memory, fire-and-forget DB write
            lang = detect_language(message) if message else "ar"
            ctx = SessionContext(language=lang)
            self._store[session_id] = ctx
            # Evict oldest sessions if limit exceeded
            if len(self._store) > self._max_sessions:
                oldest_key = next(iter(self._store))
                del self._store[oldest_key]
            if self.use_database:
                self._create_db_session(session_id, lang)
            return ctx

    def _reconstruct_context(self, conversation: dict, session_id: str) -> Optional[SessionContext]:
        meta_str = conversation.get("metadata")
        ctx = SessionContext()

        if meta_str:
            try:
                meta = json.loads(meta_str) if isinstance(meta_str, str) else meta_str
                if isinstance(meta, str):
                    meta = json.loads(meta)
                ctx.language = meta.get("language", "ar")
                ctx.pending_slot = meta.get("pending_slot")
                ctx.current_offset = meta.get("current_offset", 0)
                ctx.page_size = meta.get("page_size", 5)
                ctx.use_cursor_pagination = meta.get("use_cursor_pagination", False)
                ctx.last_clarification = meta.get("last_clarification")
                ctx.no_results_count = meta.get("no_results_count", 0)
                ctx.total_searches = meta.get("total_searches", 0)
                ctx.skipped_slots = set(meta.get("skipped_slots", []))

                if meta.get("last_search"):
                    from app.models.search_models import SearchFilters
                    ctx.last_search = SearchFilters(**meta["last_search"])

                if meta.get("user_preferences"):
                    from app.core.session_context import UserPreferences
                    ctx.user_preferences = UserPreferences(**meta["user_preferences"])
            except Exception:
                pass

        try:
            msgs = self.message_repo.get_session_messages(session_id)
            for msg in msgs:
                ctx.add_message(msg["role"], msg["content"])
        except Exception:
            pass

        return ctx

    def _create_db_session(self, session_id: str, language: str):
        try:
            meta = {"language": language}
            conversation_id = self.conversation_repo.create_conversation(session_id=session_id, metadata=meta)
            debug_log("MEMORY_DB", f"Session {session_id} → conversation {conversation_id}")
            self.analytics_repo.create_session(session_id)
        except Exception as e:
            debug_log("MEMORY_DB_ERROR", f"Failed to create DB session for {session_id}: {e}")

    async def update_context(self, session_id: str, context: SessionContext):
        async with self._lock:
            self._store[session_id] = context

    def _sync_to_db(self, session_id: str, context: SessionContext):
        """Fire-and-forget DB sync — doesn't block the response."""
        if not self.use_database:
            return
        try:
            meta = self._serialize_context(context)
            self.conversation_repo.update_metadata(session_id, meta)
            self.conversation_repo.update_last_activity(session_id)
            # Persist user preferences to dedicated table
            if context.user_id and context.user_preferences:
                p = context.user_preferences
                self.preferences_repo.save_preferences(
                    context.user_id,
                    {
                        "min_budget": p.min_budget,
                        "max_budget": p.max_budget,
                        "preferred_location": p.preferred_location,
                        "tenant_type": p.tenant_type,
                        "gender": p.gender,
                        "furnished": p.furnished,
                        "wifi": p.wifi,
                        "air_conditioning": p.air_conditioning,
                        "balcony": p.balcony,
                        "private_bathroom": p.private_bathroom,
                        "shared_room": p.shared_room,
                    },
                )
        except Exception:
            pass

    def _serialize_context(self, context: SessionContext) -> dict:
        return {
            "language": context.language,
            "pending_slot": context.pending_slot,
            "current_offset": context.current_offset,
            "page_size": context.page_size,
            "use_cursor_pagination": context.use_cursor_pagination,
            "last_clarification": context.last_clarification,
            "no_results_count": context.no_results_count,
            "total_searches": context.total_searches,
            "skipped_slots": list(context.skipped_slots),
            "last_search": context.last_search.model_dump() if context.last_search else None,
            "user_preferences": context.user_preferences.model_dump() if context.user_preferences else None,
        }

    async def _store_message_in_db(self, session_id: str, role: str, content: str, context: SessionContext, retry_count: int = 3):
        """Store message in database asynchronously in background with retry logic."""
        for attempt in range(retry_count):
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(self._store_message_in_db_sync, session_id, role, content, context),
                    timeout=5.0
                )
                return  # Success
            except asyncio.TimeoutError:
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    debug_log("DB_STORE_RETRY", f"Attempt {attempt+1} timed out, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    debug_log("DB_STORE_TIMEOUT", f"DB operation timed out after {retry_count} attempts for session {session_id}")
            except Exception as e:
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    debug_log("DB_STORE_RETRY", f"Attempt {attempt+1} failed: {e}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    debug_log("DB_STORE_ERROR", f"Failed after {retry_count} attempts: {e}")

    def _store_message_in_db_sync(self, session_id: str, role: str, content: str, context: SessionContext):
        """Synchronous DB write for message storage (called in background thread)."""
        conversation = self.conversation_repo.get_conversation_by_session(session_id)
        if conversation:
            self.message_repo.add_message(
                conversation_id=conversation["id"], role=role, content=content,
            )
            self.conversation_repo.increment_message_count(session_id)
            self.analytics_repo.increment_messages(session_id)

    async def store_message(self, session_id: str, role: str, content: str, context: SessionContext):
        context.add_message(role, content)
        await self.update_context(session_id, context)

        if self.use_database:
            asyncio.create_task(self._store_message_in_db(session_id, role, content, context))

    async def _store_messages_batch_in_db(self, session_id: str, turns: list, context: SessionContext, retry_count: int = 3):
        """Store multiple messages in database asynchronously in background with retry logic."""
        for attempt in range(retry_count):
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(self._store_messages_batch_in_db_sync, session_id, turns, context),
                    timeout=5.0
                )
                return  # Success
            except asyncio.TimeoutError:
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    debug_log("DB_STORE_RETRY", f"Batch attempt {attempt+1} timed out, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    debug_log("DB_STORE_TIMEOUT", f"Batch DB operation timed out after {retry_count} attempts for session {session_id}")
            except Exception as e:
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    debug_log("DB_STORE_RETRY", f"Batch attempt {attempt+1} failed: {e}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    debug_log("DB_STORE_ERROR", f"Batch failed after {retry_count} attempts: {e}")

    def _store_messages_batch_in_db_sync(self, session_id: str, turns: list, context: SessionContext):
        """Synchronous DB write for batch message storage (called in background thread)."""
        conversation = self.conversation_repo.get_conversation_by_session(session_id)
        if conversation:
            conv_id = conversation["id"]
            for role, content in turns:
                self.message_repo.add_message(conversation_id=conv_id, role=role, content=content)
                self.conversation_repo.increment_message_count(session_id)
                self.analytics_repo.increment_messages(session_id)

    async def store_messages_batch(self, session_id: str, turns: list, context: SessionContext):
        """Store multiple message turns in a single DB call pattern."""
        for role, content in turns:
            context.add_message(role, content)
        await self.update_context(session_id, context)

        if self.use_database:
            asyncio.create_task(self._store_messages_batch_in_db(session_id, turns, context))

    async def _record_search_in_db(self, session_id: str, context: SessionContext, search_type: str, results_count: int, filters: dict, retry_count: int = 3):
        """Record search in database asynchronously in background with retry logic."""
        for attempt in range(retry_count):
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(self._record_search_in_db_sync, session_id, context, search_type, results_count, filters),
                    timeout=5.0
                )
                return  # Success
            except asyncio.TimeoutError:
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    debug_log("DB_STORE_RETRY", f"Search record attempt {attempt+1} timed out, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    debug_log("DB_STORE_TIMEOUT", f"Search record timed out after {retry_count} attempts for session {session_id}")
            except Exception as e:
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    debug_log("DB_STORE_RETRY", f"Search record attempt {attempt+1} failed: {e}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    debug_log("DB_STORE_ERROR", f"Search record failed after {retry_count} attempts: {e}")

    def _record_search_in_db_sync(self, session_id: str, context: SessionContext, search_type: str, results_count: int, filters: dict):
        """Synchronous DB write for search recording (called in background thread)."""
        self.search_history_repo.add_entry(
            session_id=session_id, search_type=search_type, results_count=results_count,
            city=filters.get("city"), governorate=filters.get("governorate"),
            min_price=filters.get("min_price"), max_price=filters.get("max_price"), filters=filters,
        )
        self.analytics_repo.increment_searches(session_id)
        if results_count == 0:
            self.analytics_repo.increment_no_results(session_id)

    async def record_search(self, session_id: str, context: SessionContext, search_type: str, results_count: int, filters: dict):
        if self.use_database:
            asyncio.create_task(self._record_search_in_db(session_id, context, search_type, results_count, filters))

    async def _clear_context_in_db(self, session_id: str, retry_count: int = 3):
        """Clear context in database asynchronously in background with retry logic."""
        for attempt in range(retry_count):
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(self._clear_context_in_db_sync, session_id),
                    timeout=5.0
                )
                return  # Success
            except asyncio.TimeoutError:
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    debug_log("DB_STORE_RETRY", f"Clear context attempt {attempt+1} timed out, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    debug_log("DB_STORE_TIMEOUT", f"Clear context timed out after {retry_count} attempts for session {session_id}")
            except Exception as e:
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    debug_log("DB_STORE_RETRY", f"Clear context attempt {attempt+1} failed: {e}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    debug_log("DB_STORE_ERROR", f"Clear context failed after {retry_count} attempts: {e}")

    def _clear_context_in_db_sync(self, session_id: str):
        """Synchronous DB write for context clearing (called in background thread)."""
        self.analytics_repo.end_session(session_id)
        self.conversation_repo.delete_conversation(session_id)

    async def clear_context(self, session_id: str):
        async with self._lock:
            self._store.pop(session_id, None)
            if self.use_database:
                asyncio.create_task(self._clear_context_in_db(session_id))

    async def active_sessions(self) -> int:
        async with self._lock:
            return len(self._store)

    def get_context_sync(self, session_id: str, message: str = "") -> SessionContext:
        if session_id not in self._store:
            lang = detect_language(message) if message else "ar"
            self._store[session_id] = SessionContext(language=lang)
        else:
            ctx = self._store[session_id]
            if message:
                ctx.language = detect_language(message)
        return self._store[session_id]


memory_store = MemoryStore()
