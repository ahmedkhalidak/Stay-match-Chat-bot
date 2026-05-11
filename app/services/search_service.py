"""
SearchService — المحرك الرئيسي للـ chatbot
"""

import hashlib
import json
from app.core.memory_store import memory_store
from app.core.session_context import SessionContext
from app.models.search_models import SearchFilters
from app.nlp.nlp_pipeline import NLPPipeline
from app.services.knowledge_service import KnowledgeService
from app.services.chat_service import ChatService
from app.services.location_service import LocationService
from app.services.conversation_flow import ConversationFlow
from app.database.repositories.room_repository import RoomRepository
from app.database.repositories.property_repository import PropertyRepository
from app.formatters.response_formatter import ResponseFormatter
from app.utils.logger import debug_log


class SearchService:

    def __init__(self):
        self.nlp_pipeline = NLPPipeline()
        self.room_repo = RoomRepository()
        self.property_repo = PropertyRepository()
        self.formatter = ResponseFormatter()
        self.knowledge = KnowledgeService()
        self.chat = ChatService()
        self.location_service = LocationService()
        self.flow = ConversationFlow()

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

        # ── 1. NLPPipeline ───────────────────────
        filters = self.nlp_pipeline.extract(
            message=message,
            history=history_text,
            last_search=context.last_search,
        )
        debug_log("PIPELINE_FILTERS", filters.model_dump())

        intent = filters.intent or "invalid"

        # ── 2. Special intents ───────────────────
        if intent == "show_more":
            return self._handle_show_more(session_id, context, message)

        if intent == "go_back":
            return self._handle_go_back(session_id, context, message)

        # ── 3. Pending slot ──────────────────────
        if context.pending_slot:
            reply = self._handle_pending_slot(session_id, context, message, filters)
            self._save_turn(session_id, context, message, reply)
            return reply

        # ── 4. Intent routing ────────────────────
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
            reply = answer if answer else (
                "أنا بساعدك تلاقي أوضة أو شقة مناسبة في StayMatch 😊\n"
                "قولي مثلاً: \"عايز شقة في الإسماعيلية تحت 5000\"\n"
                "أو \"أوضة في الإسكندرية\" أو \"شقة كاملة في طنطا\""
            )
            self._save_turn(session_id, context, message, reply)
            return reply

        # ── 5. Apply stored user preferences ─────
        filters = self.flow.apply_preferences_to_filters(context, filters)
        debug_log("PREF_APPLIED", filters.model_dump())

        # ── 6. Smart missing info check ──────────
        context.update_preferences(filters)
        clarification, slot = self.flow.get_next_clarification(context, filters)
        if clarification:
            context.pending_slot = slot
            context.last_search = filters
            memory_store.update_context(session_id, context)
            self._save_turn(session_id, context, message, clarification)
            return clarification

        # ── 7. Defaults & Reset pagination ───────
        if not filters.sort_by:
            filters.sort_by = "relevance"
        context.reset_pagination()

        # ── 8. Execute search ────────────────────
        context.last_search = filters
        context.pending_slot = None
        memory_store.update_context(session_id, context)

        reply = self._execute_search(session_id, filters, context)
        self._save_turn(session_id, context, message, reply)
        return reply

    def _handle_show_more(self, session_id: str, context: SessionContext, message: str) -> str:
        if not context.last_search:
            return "مفيش بحث قبل كده يا صاحبي 😅\nقولي \"عايز شقة في الإسماعيلية\" مثلاً!"

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

    def _handle_pending_slot(self, session_id: str, context: SessionContext,
                             message: str, new_filters: SearchFilters) -> str:

        slot = context.pending_slot
        base = context.last_search or SearchFilters()

        if slot == "search_type":
            msg = message.lower()
            if any(k in msg for k in ["اوضة", "اوضه", "غرفة", "room", "أوضة", "غرفه"]):
                base.search_type = "room"
            elif any(k in msg for k in ["شقة مشتركة", "مشتركة", "shared", "roommate", "مع ناس"]):
                base.search_type = "shared"
            elif any(k in msg for k in ["شقة كاملة", "كاملة", "full", "لوحدي", "لنفسي"]):
                base.search_type = "full"
            elif any(k in msg for k in ["شقة", "شقه", "apartment", "شقق", "سكن"]):
                base.search_type = "property"
            else:
                base.search_type = new_filters.search_type or base.search_type

        elif slot == "location":
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

        elif slot == "price":
            price_data = new_filters
            if price_data.max_price:
                base.max_price = price_data.max_price
            if price_data.min_price:
                base.min_price = price_data.min_price
            # Also try regex from raw message
            from app.extractors.price_extractor import PriceExtractor
            pe = PriceExtractor()
            extracted = pe.extract(message)
            if extracted["max_price"]:
                base.max_price = extracted["max_price"]
            if extracted["min_price"]:
                base.min_price = extracted["min_price"]
            if base.min_price is None and base.max_price is None:
                # User said "any" or didn't specify
                pass  # Keep as None (no price filter)

        elif slot == "tenant_type":
            msg = message.lower()
            if any(k in msg for k in ["طالب", "طلاب", "student", "سكن طلبه"]):
                base.tenant_type = "student"
            elif any(k in msg for k in ["موظف", "موظفين", "worker", "عامل"]):
                base.tenant_type = "worker"
            if any(k in msg for k in ["شباب", "ولاد", "boys", "male", "رجاله"]):
                base.gender = "male"
            elif any(k in msg for k in ["بنات", "girls", "female", "سيدات", "ladies"]):
                base.gender = "female"

        elif slot == "furnished":
            msg = message.lower()
            if any(k in msg for k in ["مفروش", "مفروشة", "furnished"]):
                base.furnished = True
            elif any(k in msg for k in ["غير مفروش", "unfurnished", "فاضيه"]):
                base.furnished = False
            # Any other response = no preference

        context.pending_slot = None
        context.update_preferences(base)

        # Re-run flow check
        clarification, next_slot = self.flow.get_next_clarification(context, base)
        if clarification:
            context.pending_slot = next_slot
            context.last_search = base
            memory_store.update_context(session_id, context)
            return clarification

        if not base.sort_by:
            base.sort_by = "relevance"

        context.last_search = base
        context.reset_pagination()
        context.pending_slot = None
        memory_store.update_context(session_id, context)
        return self._execute_search(session_id, base, context)

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

            elif filters.search_type in ("property", "full", "shared"):
                debug_log("SEARCH", f"{filters.search_type} offset={offset} limit={limit}")
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

        # ── No results — smart context-aware message ─
        if not page_results and offset == 0:
            location_name = filters.city or filters.governorate or "المنطقة دي"
            search_type_name = {
                "room": "أوض",
                "property": "شقق",
                "full": "شقق كاملة",
                "shared": "شقق مشتركة",
            }.get(filters.search_type, "شقق")

            no_results_msg = (
                f"مش لاقي {search_type_name} في {location_name} حالياً 😅\n\n"
                f"ممكن تجرب:\n"
                f"• مدينة تانية (زي \"الإسماعيلية\" أو \"الإسكندرية\" أو \"طنطا\")\n"
                f"• غيّر السعر (مثلاً \"تحت 10000\")\n"
                f"• أو قولي \"أي مكان\" وهدورلك في كل مصر 😎"
            )
            context.push_search(filters, 0)
            memory_store.update_context(session_id, context)
            return no_results_msg

        context.last_results_count = len(page_results)
        memory_store.update_context(session_id, context)

        if offset == 0:
            context.push_search(filters, len(page_results))
            # Mark seen IDs
            if filters.search_type == "room":
                ids = [r.get("Id") for r in page_results if r.get("Id")]
                context.mark_seen(room_ids=ids)
            else:
                ids = [r.get("Id") for r in page_results if r.get("Id")]
                context.mark_seen(property_ids=ids)
            memory_store.update_context(session_id, context)

        if filters.search_type == "room":
            reply = self.formatter.format_rooms(page_results, filters, has_more=has_more, page_num=page_num)
        else:
            reply = self.formatter.format_properties(page_results, filters, has_more=has_more, page_num=page_num)

        # Append smart follow-up (no LLM — pure logic)
        followup = self.flow.build_smart_followup(
            context, filters, len(page_results), has_more
        )
        if followup:
            reply += "\n\n" + followup

        return reply
