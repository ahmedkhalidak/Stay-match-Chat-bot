"""
SearchService - main chatbot orchestrator.
"""

from app.core.memory_store import memory_store
from app.core.session_context import SessionContext
from app.core.conversation_memory import conversation_memory
from app.models.response_models import ChatResponse
from app.models.search_models import SearchFilters
from app.nlp.nlp_pipeline import NLPPipeline
from app.services.chat_service import ChatService
from app.services.conversation_flow import ConversationFlow
from app.services.knowledge_service import KnowledgeService
from app.services.search_executor import SearchExecutor
from app.utils.logger import debug_log

from app.services.rag_service import RagService
    
class SearchService:

    def __init__(self):
        self.nlp_pipeline = NLPPipeline()
        self.rag = RagService()
        self.chat = ChatService()
        self.flow = ConversationFlow()
        self.search_executor = SearchExecutor(flow=self.flow)

    @property
    def room_repo(self):
        return self.search_executor.room_repo

    @room_repo.setter
    def room_repo(self, repository):
        self.search_executor.room_repo = repository

    @property
    def property_repo(self):
        return self.search_executor.property_repo

    @property_repo.setter
    def property_repo(self, repository):
        self.search_executor.property_repo = repository

    def _save_turn(
        self,
        session_id: str,
        context: SessionContext,
        user_msg: str,
        response: ChatResponse,
    ):
        context.add_message("user", user_msg)
        context.add_message("assistant", response.reply)
        memory_store.update_context(session_id, context)
        
        # Also add to enhanced LangChain conversation memory
        conversation_memory.add_message(session_id, "user", user_msg)
        conversation_memory.add_message(session_id, "assistant", response.reply)

    def handle_message(self, session_id: str, message: str) -> ChatResponse:
        debug_log("SEARCH_SERVICE", f"Handling message - session: {session_id}, message: {message[:100]}...")
        context = memory_store.get_context(session_id)
        context.turn_count += 1

        # Sync with enhanced conversation memory if first message
        if context.turn_count == 1:
            conversation_memory.sync_with_session_context(session_id, context)

        # Get enhanced conversation context from LangChain memory
        enhanced_history = conversation_memory.get_conversation_context(session_id)
        history_text = context.get_history_text()
        
        # Use enhanced history if available, otherwise fall back to original
        if enhanced_history:
            history_text = enhanced_history
            debug_log("MEMORY_ENHANCED", "Using LangChain conversation memory")
        debug_log("SESSION", session_id)
        debug_log("TURN", context.turn_count)
        debug_log("MESSAGE", message)

        filters = self.nlp_pipeline.extract(
            message=message,
            history=history_text,
            last_search=context.last_search,
            pending_slot=context.pending_slot,
        )
        debug_log("PIPELINE_FILTERS", filters.model_dump())

        intent = filters.intent or "invalid"

        if intent == "show_more":
            response = self._handle_show_more(session_id, context, message)
            return response

        if intent == "go_back":
            response = self._handle_go_back(session_id, context, message)
            return response

        if intent == "small_talk":
            response = ChatResponse(
                reply=self.chat.generate_reply(message),
                response_type="small_talk",
            )
            self._save_turn(session_id, context, message, response)
            return response

        if intent == "faq":
            answer = self.rag.answer(message)
            response = ChatResponse(
                reply=answer or "مش معايا إجابة دقيقة على السؤال ده حالياً.",
                response_type="faq",
            )
            self._save_turn(session_id, context, message, response)
            return response

        if intent == "invalid":
            answer = self.rag.answer(message)
            if answer:
                response = ChatResponse(
                    reply=answer,
                    response_type="faq",
                )
            else:
                response = ChatResponse(
                    reply=(
                        "أقدر أساعدك تلاقي أوضة أو شقة مناسبة.\n"
                        "ابدأ مثلاً بـ \"أوضة\" أو \"شقة كاملة\"."
                    ),
                    response_type="fallback",
                    suggestions=self.flow.get_slot_suggestions("search_type"),
                )
            self._save_turn(session_id, context, message, response)
            return response

        filters = self.flow.apply_preferences_to_filters(context, filters)
        filters = self.flow.apply_user_overrides(context, filters, message)
        self.flow.sync_skipped_slots(context, filters)
        context.update_preferences(filters)
        debug_log("PREF_APPLIED", filters.model_dump())

        clarification, slot = self.flow.get_next_clarification(context, filters)
        if clarification:
            context.pending_slot = slot
            context.last_search = filters.model_copy(deep=True)
            response = ChatResponse(
                reply=clarification,
                response_type="clarification",
                pending_slot=slot,
                filters=filters,
                suggestions=self.flow.get_slot_suggestions(slot),
            )
            self._save_turn(session_id, context, message, response)
            return response

        if not filters.sort_by:
            filters.sort_by = "relevance"

        context.reset_pagination()
        context.use_cursor_pagination = False  # Disabled temporarily due to FreeTDS parameter limit
        context.last_search = filters.model_copy(deep=True)
        context.pending_slot = None
        memory_store.update_context(session_id, context)

        response = self.search_executor.execute(filters, context)
        self._save_turn(session_id, context, message, response)
        return response

    def _handle_show_more(
        self,
        session_id: str,
        context: SessionContext,
        message: str,
    ) -> ChatResponse:
        if not context.last_search:
            response = ChatResponse(
                reply="لسه مفيش بحث سابق أطلع منه نتائج إضافية.",
                response_type="fallback",
                suggestions=self.flow.get_slot_suggestions("search_type"),
            )
            self._save_turn(session_id, context, message, response)
            return response

        filters = context.last_search.model_copy(deep=True)
        
        # Disable cursor-based pagination due to FreeTDS parameter limit
        context.use_cursor_pagination = False
        
        # Simply increment offset
        previous_offset = context.current_offset
        context.current_offset += context.page_size
        debug_log("SHOW_MORE", f"Previous offset: {previous_offset}, New offset: {context.current_offset}, Session: {session_id}")
        
        memory_store.update_context(session_id, context)

        response = self.search_executor.execute(filters, context)
        
        # Verify offset was not overwritten
        loaded_context = memory_store.get_context(session_id)
        debug_log("SHOW_MORE_VERIFY", f"Saved offset: {context.current_offset}, Loaded offset: {loaded_context.current_offset}")
        
        self._save_turn(session_id, context, message, response)
        return response

    def _handle_go_back(
        self,
        session_id: str,
        context: SessionContext,
        message: str,
    ) -> ChatResponse:
        prev_filters = context.go_back()
        if not prev_filters:
            response = ChatResponse(
                reply="مفيش بحث أقدم أرجع له.",
                response_type="fallback",
            )
            self._save_turn(session_id, context, message, response)
            return response

        context.reset_pagination()
        context.last_search = prev_filters.model_copy(deep=True)
        memory_store.update_context(session_id, context)

        response = self.search_executor.execute(prev_filters, context)
        self._save_turn(session_id, context, message, response)
        return response
