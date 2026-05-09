from app.core.memory_store import memory_store
from app.services.knowledge_service import (
    KnowledgeService
)
from app.services.chat_service import (
    ChatService
)
from app.extractors.query_extractor import (
    QueryExtractor
)

from app.extractors.followup_extractor import (
    FollowUpExtractor
)

from app.services.intent_service import (
    IntentService
)

from app.database.repositories.room_repository import (
    RoomRepository
)

from app.database.repositories.property_repository import (
    PropertyRepository
)

from app.formatters.response_formatter import (
    ResponseFormatter
)

from app.validators.filter_validator import (
    FilterValidator
)

from app.utils.logger import debug_log


class SearchService:

    def __init__(self):

        self.query_extractor = (
            QueryExtractor()
        )

        self.followup_extractor = (
            FollowUpExtractor()
        )

        self.validator = (
            FilterValidator()
        )

        self.room_repository = (
            RoomRepository()
        )

        self.property_repository = (
            PropertyRepository()
        )

        self.formatter = (
            ResponseFormatter()
        )
        self.knowledge_service = (
             KnowledgeService()
        )
        self.chat_service = (
            ChatService()
        )
    def handle_message(
        self,
        session_id: str,
        message: str,
    ):

        # ── Load context ─────────────────────────
        context = memory_store.get_context(
            session_id
        )

        debug_log(
            "SESSION",
            session_id,
        )

        debug_log(
            "MESSAGE",
            message,
        )

        debug_log(
            "LAST SEARCH",
            context.last_search,
        )

        debug_log(
            "PENDING SLOT",
            context.pending_slot,
        )

        # ── Detect intent ────────────────────────
   # ──────────────────────────────────
        # AI Extraction
        # ──────────────────────────────────

        filters = (
            self.query_extractor.extract(
                message
            )
        )

        debug_log(
            "RAW AI FILTERS",
            filters,
        )

        # ──────────────────────────────────
        # Validate Filters
        # ──────────────────────────────────

        filters = (
            self.validator.validate(
                filters
            )
        )

        debug_log(
            "VALIDATED FILTERS",
            filters,
        )

        # ──────────────────────────────────
        # AI Intent
        # ──────────────────────────────────

        intent = (
            filters.intent
        )

        debug_log(
            "AI INTENT",
            intent,
)
        # ── Invalid / unrelated ─────────────────

        if intent == "invalid":

            knowledge_answer = (
                self.knowledge_service.find_answer(
                    message
                )
            )

            if knowledge_answer:

                debug_log(
                    "KNOWLEDGE MATCH",
                    knowledge_answer,
                )

                return knowledge_answer

            return (
                "أنا بساعد في البحث عن "
                "الأوض والشقق داخل "
                "StayMatch 😊"
            )
        # ── Empty messages ──────────────────────

        if intent == "empty":

            return (
                "ممكن توضح طلبك أكتر؟ 😊"
            )
            # ── Small Talk ───────────────────────

        if intent == "small_talk":

            return (
                self.chat_service
                .generate_reply(
                    message
                )
            )

        if intent == "faq":

            knowledge_answer = (
                self.knowledge_service.find_answer(
                    message
                )
            )

            if knowledge_answer:

                debug_log(
                    "KNOWLEDGE MATCH",
                    knowledge_answer,
                )

                return knowledge_answer

        # ── Handle pending slot ──────────────────
        if context.pending_slot:

            pending_filters = (
                self.query_extractor.extract(
                    message
                )
            )

            pending_filters = (
                self.validator.validate(
                    pending_filters
                )
            )

            debug_log(
                "PENDING FILTERS",
                pending_filters,
            )

            if context.last_search:

                filters = (
                    self.query_extractor.merge_filters(
                        context.last_search,
                        pending_filters,
                    )
                )

            else:

                filters = pending_filters

            context.pending_slot = None

        else:

            # ── AI Extraction ────────────────────
            new_filters = (
                self.query_extractor.extract(
                    message
                )
            )

            debug_log(
                "RAW AI FILTERS",
                new_filters,
            )

            # ── Validate AI output ───────────────
            new_filters = self.validator.validate(
                new_filters
            )

            debug_log(
                "VALIDATED FILTERS",
                new_filters,
            )

            # ── Follow-up merge ──────────────────
            if (
                intent == "follow_up"
                and context.last_search
            ):

                debug_log(
                    "FLOW",
                    "FOLLOW-UP MERGE",
                )

                filters = (
                    self.query_extractor.merge_filters(
                        context.last_search,
                        new_filters,
                    )
                )

            else:

                debug_log(
                    "FLOW",
                    "NEW SEARCH",
                )

                filters = new_filters

                # ── Infer search type ────────────
                if (
                    not filters.search_type
                    and context.last_search
                ):

                    filters.search_type = (
                        context.last_search.search_type
                    )

                    debug_log(
                        "INFERRED SEARCH TYPE",
                        filters.search_type,
                    )

        # ── Clarification logic ──────────────────

        if not filters.search_type:

            context.pending_slot = (
                "search_type"
            )

            context.last_search = filters

            memory_store.update_context(
                session_id,
                context,
            )

            return (
                "عايز شقة ولا أوضة؟ 🏠"
            )

        if (
            filters.search_type == "room"
            and not filters.city
        ):

            context.pending_slot = "city"

            context.last_search = filters

            memory_store.update_context(
                session_id,
                context,
            )

            return "في أي مدينة؟ 📍"

        # ── Default sorting ──────────────────────
        if not filters.sort_by:

            filters.sort_by = "relevance"

        # ── Save state ───────────────────────────
        context.last_search = filters

        memory_store.update_context(
            session_id,
            context,
        )

        debug_log(
            "FINAL FILTERS",
            filters,
        )

        # ── Room search ──────────────────────────
        if filters.search_type == "room":

            rooms = self.room_repository.search(
                filters
            )

            debug_log(
                "ROOM RESULTS",
                len(rooms),
            )

            return self.formatter.format_rooms(
                rooms
            )

        # ── Property search ──────────────────────
        elif filters.search_type == "property":

            properties = (
                self.property_repository.search(
                    filters
                )
            )

            debug_log(
                "PROPERTY RESULTS",
                len(properties),
            )

            return (
                self.formatter.format_properties(
                    properties
                )
            )

        # ── Fallback ─────────────────────────────
        debug_log(
            "FALLBACK",
            "No valid search type",
        )

        return (
            "اسألني عن الشقق أو الأوض المتاحة 😊"
        )