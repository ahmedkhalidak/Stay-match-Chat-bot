import time

from app.core.memory_store import memory_store
from app.core.session_context import SessionContext, UserPreferences
from app.models.response_models import ChatResponse, QuickReply
from app.models.search_models import SearchFilters
from app.nlp.nlp_pipeline import NLPPipeline
from app.services.chat_service import ChatService
from app.services.conversation_flow import ConversationFlow
from app.services.search_executor import SearchExecutor
from app.utils.logger import debug_log
from app.utils.bilingual_responses import t
from app.utils.language_detector import resolve_response_language
from app.services.faq_service import FaqService
from app.services.recommendation_client import (
    get_recommendation_scores, get_room_recommendation_scores,
    send_interaction, trigger_preferences_sync
)


class SearchService:

    def __init__(self):
        self.nlp_pipeline = NLPPipeline()
        self.faq = FaqService()
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

    def _log_response_timing(self, session_id: str, intent: str, response: ChatResponse, started_at: float):
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        debug_log(
            "RESPONSE_TIMING",
            f"session={session_id}, intent={intent}, type={response.response_type}, duration_ms={duration_ms}",
        )

    async def _finish_response(
        self,
        session_id: str,
        context: SessionContext,
        response: ChatResponse,
        started_at: float,
        intent: str,
    ) -> ChatResponse:
        await memory_store.store_message(session_id, "assistant", response.reply, context)
        self._bg_save(session_id, context)
        self._log_response_timing(session_id, intent, response, started_at)
        return response

    def _shortcut_response(self, message: str, context: SessionContext, lang: str) -> ChatResponse | None:
        normalized = message.strip().lower()

        apartment_commands = {
            "find_full_apartment", "find_apartment", "full_apartment",
            "إيجاد شقة كاملة", "ايجاد شقة كاملة", "شقة كاملة", "شقه كامله",
        }
        room_commands = {
            "find_room", "find_rooms", "room",
            "إيجاد أوضة / غرفة", "ايجاد اوضة", "ايجاد غرفة", "أوضة", "اوضة", "غرفة",
        }

        if normalized in {cmd.lower() for cmd in apartment_commands}:
            filters = SearchFilters(intent="property_search", search_type="full", housing_type="apartment")
            context.pending_slot = "location"
            context.last_search = filters.model_copy(deep=True)
            return ChatResponse(
                reply=t("ASK_LOCATION", lang),
                response_type="find_apartment",
                pending_slot="location",
                filters=filters,
                suggestions=self.flow.get_slot_suggestions("location", lang),
            )

        if normalized in {cmd.lower() for cmd in room_commands}:
            filters = SearchFilters(intent="room_search", search_type="room", housing_type="room")
            context.pending_slot = "location"
            context.last_search = filters.model_copy(deep=True)
            return ChatResponse(
                reply=t("ASK_LOCATION", lang),
                response_type="find_room",
                pending_slot="location",
                filters=filters,
                suggestions=self.flow.get_slot_suggestions("location", lang),
            )

        shortcut_replies = {
            "how_to_add_property": (
                "add_property_help",
                "من شاشة إضافة عقار، ارفع الصور واكتب السعر والموقع والمرافق ثم انشر الإعلان.",
                [QuickReply(label="الدعم الفني", value="support_help"), QuickReply(label="إيجاد شقة كاملة", value="find_full_apartment")],
            ),
            "add_property_help": (
                "add_property_help",
                "من شاشة إضافة عقار، ارفع الصور واكتب السعر والموقع والمرافق ثم انشر الإعلان.",
                [QuickReply(label="الدعم الفني", value="support_help"), QuickReply(label="إيجاد شقة كاملة", value="find_full_apartment")],
            ),
            "booking_help": (
                "booking_help",
                "اختار العقار المناسب، افتح التفاصيل، وبعدها تواصل مع المالك لتأكيد الحجز.",
                [QuickReply(label="إيجاد شقة كاملة", value="find_full_apartment"), QuickReply(label="إيجاد أوضة", value="find_room")],
            ),
            "ratings_help": (
                "ratings_help",
                "التقييمات بتساعدك تعرف جودة العقار والمالك من تجارب المستخدمين السابقين.",
                [QuickReply(label="طريقة الحجز", value="booking_help"), QuickReply(label="الدعم الفني", value="support_help")],
            ),
            "support_help": (
                "support_help",
                "لو عندك مشكلة، ابعت تفاصيلها من الدعم الفني داخل التطبيق أو اكتبها هنا.",
                [QuickReply(label="طريقة الحجز", value="booking_help"), QuickReply(label="إضافة عقار", value="how_to_add_property")],
            ),
        }

        arabic_aliases = {
            "إضافة عقار": "how_to_add_property",
            "اضافة عقار": "how_to_add_property",
            "طريقة الحجز": "booking_help",
            "نظام التقييمات": "ratings_help",
            "الدعم الفني": "support_help",
        }
        command = arabic_aliases.get(message.strip(), normalized)
        if command in shortcut_replies:
            response_type, reply, suggestions = shortcut_replies[command]
            return ChatResponse(reply=reply, response_type=response_type, suggestions=suggestions)

        return None

    async def handle_message(self, session_id: str, message: str, user_id: str | None = None) -> ChatResponse:
        started_at = time.perf_counter()
        user_id = user_id or session_id
        debug_log("SEARCH_SERVICE", f"session={session_id}, msg={message[:100]}, user={user_id}")

        current_message_language = resolve_response_language(message)
        context = await memory_store.get_context(session_id, message)
        context.language = current_message_language
        context.turn_count += 1
        lang = current_message_language

        if not context.user_id:
            context.user_id = user_id
            memory_store.conversation_repo.update_user_id(session_id, user_id)
            # Load user preferences from database
            prefs = memory_store.preferences_repo.load_preferences(user_id)
            if prefs:
                p = context.user_preferences
                p.min_budget = prefs.get("min_budget")
                p.max_budget = prefs.get("max_budget")
                p.preferred_location = prefs.get("preferred_location")
                p.tenant_type = prefs.get("tenant_type")
                p.gender = prefs.get("gender")
                p.furnished = prefs.get("furnished")
                p.wifi = prefs.get("wifi")
                p.air_conditioning = prefs.get("air_conditioning")
                p.balcony = prefs.get("balcony")
                p.private_bathroom = prefs.get("private_bathroom")
                p.shared_room = prefs.get("shared_room")
                debug_log("PREFERENCES_LOADED", f"Loaded preferences for user {user_id}")

        shortcut_response = self._shortcut_response(message, context, lang)
        if shortcut_response:
            await memory_store.store_message(session_id, "user", message, context)
            return await self._finish_response(
                session_id, context, shortcut_response, started_at, shortcut_response.response_type
            )

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
        await memory_store.store_message(session_id, "user", message, context)

        if intent == "show_more":
            response = self._handle_show_more(session_id, context, message, lang)
            return await self._finish_response(session_id, context, response, started_at, intent)

        if intent == "go_back":
            response = self._handle_go_back(session_id, context, message, lang)
            return await self._finish_response(session_id, context, response, started_at, intent)

        if intent == "small_talk":
            response = ChatResponse(
                reply=await self.chat.generate_reply(message, lang),
                response_type="small_talk",
            )
            return await self._finish_response(session_id, context, response, started_at, intent)

        if intent == "faq":
            answer = await self.faq.answer(message)
            if not answer:
                answer = t("FAQ_NO_ANSWER", lang)
            response = ChatResponse(reply=answer, response_type="faq")
            return await self._finish_response(session_id, context, response, started_at, intent)

        if intent == "invalid":
            answer = await self.faq.answer(message)
            if answer:
                response = ChatResponse(reply=answer, response_type="faq")
            else:
                response = ChatResponse(
                    reply=t("FALLBACK", lang),
                    response_type="fallback",
                    suggestions=self.flow.get_slot_suggestions("search_type", lang),
                )
            return await self._finish_response(session_id, context, response, started_at, intent)

        filters = self.flow.apply_preferences_to_filters(context, filters, message)
        filters = self.flow.apply_user_overrides(context, filters, message)
        self.flow.sync_skipped_slots(context, filters)
        context.update_preferences(filters)
        if context.user_id and context.user_preferences:
            trigger_preferences_sync()

        clarification, slot = self.flow.get_next_clarification(context, filters, lang=lang)
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
            return await self._finish_response(session_id, context, response, started_at, intent)

        if not filters.sort_by:
            filters.sort_by = "relevance"

        context.reset_pagination()
        context.last_search = filters.model_copy(deep=True)
        context.pending_slot = None

        response = self.search_executor.execute(filters, context, lang=lang)

        if self.flow.should_ask_housing_type_clarification(context, filters, context.last_results_count):
            location_name = filters.city or filters.governorate or ""
            clarification, slot = self.flow.get_housing_type_clarification(
                context, filters, context.last_results_count, location_name, lang=lang
            )
            context.pending_slot = slot
            response = ChatResponse(
                reply=clarification,
                response_type="clarification",
                pending_slot=slot,
                filters=filters,
                suggestions=self.flow.get_slot_suggestions(slot, lang),
            )

        return await self._finish_response(session_id, context, response, started_at, intent)

    def _handle_show_more(self, session_id: str, context: SessionContext, message: str, lang: str) -> ChatResponse:
        if not context.last_search:
            return ChatResponse(
                reply=t("NO_PREVIOUS_SEARCH", lang),
                response_type="fallback",
                suggestions=self.flow.get_slot_suggestions("search_type", lang),
            )
        filters = context.last_search.model_copy(deep=True)
        context.current_offset += context.page_size
        return self.search_executor.execute(filters, context, lang=lang)

    def _handle_go_back(self, session_id: str, context: SessionContext, message: str, lang: str) -> ChatResponse:
        prev_filters = context.go_back()
        if not prev_filters:
            return ChatResponse(reply=t("NO_PREVIOUS_HISTORY", lang), response_type="fallback")
        context.reset_pagination()
        context.last_search = prev_filters.model_copy(deep=True)
        return self.search_executor.execute(prev_filters, context, lang=lang)
