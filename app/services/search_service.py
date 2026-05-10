"""
SearchService — المحرك الرئيسي للـ chatbot (نسخة محسّنة + LangChain + Pagination)
Flow محترم ومصري فريندلي 🇪🇬
"""

import hashlib
import json
from app.core.memory_store import memory_store
from app.core.session_context import SessionContext
from app.models.search_models import SearchFilters
from app.extractors.query_extractor import QueryExtractor
from app.extractors.filter_extractor import FilterExtractor
from app.services.knowledge_service import KnowledgeService
from app.services.chat_service import ChatService
from app.services.location_service import LocationService
from app.database.repositories.room_repository import RoomRepository
from app.database.repositories.property_repository import PropertyRepository
from app.formatters.response_formatter import ResponseFormatter
from app.utils.logger import debug_log


class SearchService:

    def __init__(self):
        self.query_extractor = QueryExtractor()
        self.filter_extractor = FilterExtractor()
        self.room_repo = RoomRepository()
        self.property_repo = PropertyRepository()
        self.formatter = ResponseFormatter()
        self.knowledge = KnowledgeService()
        self.chat = ChatService()
        self.location_service = LocationService()

    def _filters_hash(self, filters: SearchFilters) -> str:
        data = json.dumps(filters.model_dump(), sort_keys=True, default=str)
        return hashlib.md5(data.encode()).hexdigest()

    def _save_turn(self, session_id: str, context: SessionContext, user_msg: str, assistant_msg: str):
        context.add_message("user", user_msg)
        context.add_message("assistant", assistant_msg)
        memory_store.update_context(session_id, context)

    def handle_message(self, session_id: str, message: str) -> str:

        context = memory_store.get_context(session_id)
        context.turn_count += 1

        history_text = context.get_history_text()
        debug_log("SESSION", session_id)
        debug_log("TURN", context.turn_count)
        debug_log("MESSAGE", message)

        # ── 2. AI Extraction ─────────────────────
        filters = self.query_extractor.extract(message, history_text)
        debug_log("AI_FILTERS", filters.model_dump())

        intent = filters.intent or "invalid"

        # ── 3. Special intents ───────────────────
        if intent == "show_more":
            return self._handle_show_more(session_id, context, message)

        if intent == "go_back":
            return self._handle_go_back(session_id, context, message)

        # ── 4. Pending slot ──────────────────────
        if context.pending_slot:
            reply = self._handle_pending_slot(session_id, context, message, filters)
            self._save_turn(session_id, context, message, reply)
            return reply

        # ── 5. Intent routing ────────────────────
        if intent == "small_talk":
            reply = self.chat.generate_reply(message)
            self._save_turn(session_id, context, message, reply)
            return reply

        if intent == "faq":
            answer = self.knowledge.find_answer(message)
            reply = answer if answer else "مش عارف أجاوب على ده دلوقتي 😅 جرب تسألني عن الأوض والشقق!"
            self._save_turn(session_id, context, message, reply)
            return reply

        if intent == "invalid":
            answer = self.knowledge.find_answer(message)
            reply = answer if answer else "أنا بساعدك تلاقي أوضة أو شقة مناسبة في StayMatch 😊\nقولي مثلاً: \"عايز شقة في القاهرة تحت 5000\""
            self._save_turn(session_id, context, message, reply)
            return reply

        # ── 6. Follow-up / Clarification / New ───
        if intent == "follow_up" and context.last_search:
            debug_log("FLOW", "FOLLOW_UP_MERGE")
            filters = self.query_extractor.merge_filters(context.last_search, filters)
            if not filters.search_type:
                filters.search_type = context.last_search.search_type

        elif intent == "remove_filter" and context.last_search:
            debug_log("FLOW", "REMOVE_FILTER")
            filters = self._handle_remove_filter(context.last_search, filters)

        elif intent == "clarification" and context.last_search:
            debug_log("FLOW", "CLARIFICATION_MERGE")
            filters = self.query_extractor.merge_filters(context.last_search, filters)

        else:
            debug_log("FLOW", "NEW_SEARCH")
            if not filters.search_type and context.last_search:
                filters.search_type = context.last_search.search_type

        # ── 7. Check missing info (Egyptian friendly) ─
        clarification = self._check_missing(session_id, context, filters)
        if clarification:
            self._save_turn(session_id, context, message, clarification)
            return clarification

        # ── 8. Defaults & Reset pagination ───────
        if not filters.sort_by:
            filters.sort_by = "relevance"
        context.reset_pagination()

        # ── 9. Execute search ────────────────────
        context.last_search = filters
        memory_store.update_context(session_id, context)

        reply = self._execute_search(session_id, filters, context)
        self._save_turn(session_id, context, message, reply)
        return reply

    def _handle_show_more(self, session_id: str, context: SessionContext, message: str) -> str:
        if not context.last_search:
            return "مفيش بحث قبل كده يا صاحبي 😅\nقولي \"عايز شقة في القاهرة\" مثلاً!"

        filters = context.last_search
        context.current_offset += context.page_size
        memory_store.update_context(session_id, context)

        reply = self._execute_search(session_id, filters, context)
        self._save_turn(session_id, context, message, reply)
        return reply

    def _handle_go_back(self, session_id: str, context: SessionContext, message: str) -> str:
        prev_filters = context.go_back()
        if not prev_filters:
            return "مفيش بحث قبل كده يا صاحبي 😅"

        context.reset_pagination()
        context.last_search = prev_filters
        memory_store.update_context(session_id, context)

        reply = self._execute_search(session_id, prev_filters, context)
        self._save_turn(session_id, context, message, reply)
        return reply

    def _handle_remove_filter(self, base: SearchFilters, update: SearchFilters) -> SearchFilters:
        merged = base.model_copy(deep=True)
        for field, value in update.model_dump().items():
            if field == "intent":
                continue
            if value is False:
                setattr(merged, field, None)
            elif value is not None:
                setattr(merged, field, value)
        return merged

    def _handle_pending_slot(self, session_id: str, context: SessionContext,
                             message: str, new_filters: SearchFilters) -> str:

        slot = context.pending_slot
        base = context.last_search or SearchFilters()

        if slot == "search_type":
            msg = message.lower()
            if any(k in msg for k in ["اوضة", "اوضه", "غرفة", "room", "أوضة", "غرفه"]):
                base.search_type = "room"
            elif any(k in msg for k in ["شقة", "شقه", "apartment", "شقق", "سكن"]):
                base.search_type = "property"
            else:
                base.search_type = new_filters.search_type or base.search_type

        elif slot == "city":
            if new_filters.city:
                base.city = new_filters.city
            elif new_filters.governorate:
                base.governorate = new_filters.governorate
            else:
                loc = self.location_service.detect_location(message)
                if loc:
                    if loc["type"] == "city":
                        base.city = loc["en"]
                    else:
                        base.governorate = loc["en"]

        context.pending_slot = None

        clarification = self._check_missing(session_id, context, base)
        if clarification:
            return clarification

        if not base.sort_by:
            base.sort_by = "relevance"

        context.last_search = base
        context.reset_pagination()
        memory_store.update_context(session_id, context)
        return self._execute_search(session_id, base, context)

    def _check_missing(self, session_id: str, context: SessionContext,
                       filters: SearchFilters) -> str | None:
        """يسأل بطريقة مصرية فريندلي لو فيه معلومات ناقصة"""

        if not filters.search_type:
            context.pending_slot = "search_type"
            context.last_search = filters
            memory_store.update_context(session_id, context)
            return (
                "أهلاً بيك في StayMatch! 😄\n"
                "عايز تسكن إزاي؟\n\n"
                "1️⃣ شقة كاملة (ليك لوحدك أو مع صحابك)\n"
                "2️⃣ أوضة في شقة مشتركة (مع roommates)\n\n"
                "قولي \"شقة\" أو \"أوضة\" وانا هساعدك 👇"
            )

        if filters.search_type == "room" and not filters.city and not filters.governorate:
            context.pending_slot = "city"
            context.last_search = filters
            memory_store.update_context(session_id, context)
            return (
                "تمام، عايز الأوضة فين؟ 📍\n\n"
                "ممكن تقولي اسم المدينة أو المنطقة، مثلاً:\n"
                "• القاهرة\n"
                "• مدينة نصر\n"
                "• إسماعيلية\n"
                "• المعادي\n\n"
                "أو اكتب أي منطقة انت عايزها 👇"
            )

        if filters.search_type == "property" and not filters.city and not filters.governorate:
            # للشقق: نسأل بس مش نلزم (ممكن يبحث في كل مصر)
            # بس لو هو قال "عايز شقة" بس، نسأله عشان النتائج تبقى أحسن
            context.pending_slot = "city"
            context.last_search = filters
            memory_store.update_context(session_id, context)
            return (
                "عايز الشقة فين بالظبط؟ 📍\n\n"
                "ممكن تقولي المدينة أو المنطقة، زي:\n"
                "• القاهرة\n"
                "• إسماعيلية\n"
                "• مدينة نصر\n"
                "• الشروق\n\n"
                "أو قولي \"أي مكان\" وهدورلك في كل المحافظات 😎"
            )

        return None

    def _execute_search(self, session_id: str, filters: SearchFilters, context: SessionContext) -> str:

        cache_key = self._filters_hash(filters)
        offset = context.current_offset
        limit = context.page_size
        page_num = (offset // limit) + 1

        if cache_key == context.cache_key and context.cached_results:
            all_results = context.cached_results
            page_results = all_results[offset:offset + limit]
            has_more = len(all_results) > offset + limit
        else:
            if filters.search_type == "room":
                debug_log("SEARCH", f"room offset={offset} limit={limit}")
                page_results = self.room_repo.search(filters, offset=offset, limit=limit)
                next_page = self.room_repo.search(filters, offset=offset + limit, limit=1)
                has_more = len(next_page) > 0

            elif filters.search_type == "property":
                debug_log("SEARCH", f"property offset={offset} limit={limit}")
                page_results = self.property_repo.search(filters, offset=offset, limit=limit)
                next_page = self.property_repo.search(filters, offset=offset + limit, limit=1)
                has_more = len(next_page) > 0

            else:
                return "اسألني عن الشقق أو الأوض المتاحة 😊"

            if offset == 0:
                context.cache_key = cache_key
                context.cached_results = list(page_results)
            else:
                context.cached_results.extend(list(page_results))

        context.last_results_count = len(page_results)
        memory_store.update_context(session_id, context)

        if offset == 0:
            context.push_search(filters, len(page_results))
            memory_store.update_context(session_id, context)

        if filters.search_type == "room":
            reply = self.formatter.format_rooms(page_results, filters, has_more=has_more, page_num=page_num)
        else:
            reply = self.formatter.format_properties(page_results, filters, has_more=has_more, page_num=page_num)

        return reply
