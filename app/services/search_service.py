from app.core.memory_store import memory_store
from app.core.session_context import SessionContext
from app.models.response_models import ChatResponse
from app.models.search_models import SearchFilters
from app.nlp.nlp_pipeline import NLPPipeline
from app.services.chat_service import ChatService
from app.services.conversation_flow import ConversationFlow
from app.services.search_executor import SearchExecutor
from app.utils.logger import debug_log
from app.utils.bilingual_responses import t
from app.services.rag_service import RagService
from app.services.recommendation_client import (
    get_recommendation_scores, get_room_recommendation_scores,
    send_interaction, trigger_preferences_sync
)


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

    def _bg_save(self, session_id: str, context: SessionContext):
        """Fire-and-forget DB persistence — doesn't block the response."""
        memory_store._sync_to_db(session_id, context)

    async def handle_message(self, session_id: str, message: str) -> ChatResponse:
        debug_log("SEARCH_SERVICE", f"session={session_id}, msg={message[:100]}")

        context = await memory_store.get_context(session_id, message)
        context.turn_count += 1
        lang = context.language

        history_text = context.get_history_text()
        filters = self.nlp_pipeline.extract(
            message=message,
            history=history_text,
            last_search=context.last_search,
            pending_slot=context.pending_slot,
        )

        if context.last_search and filters.housing_type and context.last_search.housing_type:
            if filters.housing_type != context.last_search.housing_type:
                context.reset_pagination()
                context.seen_property_ids.clear()
                context.seen_room_ids.clear()
                context.user_preferences = type(context.user_preferences)()
                context.user_preferences.housing_type = filters.housing_type
                for attr in ["furnished", "wifi", "balcony", "private_bathroom", "air_conditioning",
                             "gender", "tenant_type", "min_price", "max_price", "sort_by"]:
                    setattr(filters, attr, None)
                if not filters.city and not filters.governorate:
                    filters.city = context.last_search.city
                    filters.governorate = context.last_search.governorate

        intent = filters.intent or "invalid"
        context.add_message("user", message)

        if intent == "show_more":
            response = self._handle_show_more(session_id, context, message, lang)
            context.add_message("assistant", response.reply)
            self._bg_save(session_id, context)
            return response

        if intent == "go_back":
            response = self._handle_go_back(session_id, context, message, lang)
            context.add_message("assistant", response.reply)
            self._bg_save(session_id, context)
            return response

        if intent == "small_talk":
            response = ChatResponse(
                reply=self.chat.generate_reply(message, lang),
                response_type="small_talk",
            )
            context.add_message("assistant", response.reply)
            self._bg_save(session_id, context)
            return response

        if intent == "faq":
            answer = self.rag.answer(message, lang=lang)
            if not answer:
                answer = t("FAQ_NO_ANSWER", lang)
            response = ChatResponse(reply=answer, response_type="faq")
            context.add_message("assistant", response.reply)
            self._bg_save(session_id, context)
            return response

        if intent == "invalid":
            answer = self.rag.answer(message, lang=lang)
            if answer:
                response = ChatResponse(reply=answer, response_type="faq")
            else:
                response = ChatResponse(
                    reply=t("FALLBACK", lang),
                    response_type="fallback",
                    suggestions=self.flow.get_slot_suggestions("search_type", lang),
                )
            context.add_message("assistant", response.reply)
            self._bg_save(session_id, context)
            return response

        filters = self.flow.apply_preferences_to_filters(context, filters, message)
        filters = self.flow.apply_user_overrides(context, filters, message)
        self.flow.sync_skipped_slots(context, filters)
        context.update_preferences(filters)
        if context.user_id and context.user_preferences:
            trigger_preferences_sync()

        clarification, slot = self.flow.get_next_clarification(context, filters)
        if clarification:
            context.pending_slot = slot
            context.last_search = filters.model_copy(deep=True)
            response = ChatResponse(
                reply=clarification,
                response_type="clarification",
                pending_slot=slot,
                filters=filters,
                suggestions=self.flow.get_slot_suggestions(slot, lang),
            )
            context.add_message("assistant", response.reply)
            self._bg_save(session_id, context)
            return response

        if not filters.sort_by:
            filters.sort_by = "relevance"

        context.reset_pagination()
        context.last_search = filters.model_copy(deep=True)
        context.pending_slot = None

        response = self.search_executor.execute(filters, context)

        if self.flow.should_ask_housing_type_clarification(context, filters, context.last_results_count):
            location_name = filters.city or filters.governorate or ""
            clarification, slot = self.flow.get_housing_type_clarification(
                context, filters, context.last_results_count, location_name
            )
            context.pending_slot = slot
            response = ChatResponse(
                reply=clarification,
                response_type="clarification",
                pending_slot=slot,
                filters=filters,
                suggestions=self.flow.get_slot_suggestions(slot, lang),
            )

        context.add_message("assistant", response.reply)
        self._bg_save(session_id, context)
        return response

    def _handle_show_more(self, session_id: str, context: SessionContext, message: str, lang: str) -> ChatResponse:
        if not context.last_search:
            return ChatResponse(
                reply=t("NO_PREVIOUS_SEARCH", lang),
                response_type="fallback",
                suggestions=self.flow.get_slot_suggestions("search_type", lang),
            )
        filters = context.last_search.model_copy(deep=True)
        context.current_offset += context.page_size
        return self.search_executor.execute(filters, context)

    def _handle_go_back(self, session_id: str, context: SessionContext, message: str, lang: str) -> ChatResponse:
        prev_filters = context.go_back()
        if not prev_filters:
            return ChatResponse(reply=t("NO_PREVIOUS_HISTORY", lang), response_type="fallback")
        context.reset_pagination()
        context.last_search = prev_filters.model_copy(deep=True)
        return self.search_executor.execute(prev_filters, context)