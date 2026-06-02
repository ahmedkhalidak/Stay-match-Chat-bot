import hashlib
import json

from app.core.session_context import SessionContext
from app.database.repositories.property_repository import PropertyRepository
from app.database.repositories.room_repository import RoomRepository
from app.formatters.response_formatter import ResponseFormatter
from app.models.response_models import ChatResponse, PaginationMeta
from app.models.search_models import SearchFilters
from app.services.conversation_flow import ConversationFlow
from app.utils.logger import debug_log
from app.utils.bilingual_responses import t


class SearchExecutor:
    def __init__(
        self,
        room_repo: RoomRepository | None = None,
        property_repo: PropertyRepository | None = None,
        formatter: ResponseFormatter | None = None,
        flow: ConversationFlow | None = None,
    ):
        self.room_repo = room_repo or RoomRepository()
        self.property_repo = property_repo or PropertyRepository()
        self.formatter = formatter or ResponseFormatter()
        self.flow = flow or ConversationFlow()

    def execute(self, filters: SearchFilters, context: SessionContext) -> ChatResponse:
        lang = context.language
        cache_key = self._filters_hash(filters)

        offset = context.current_offset
        limit = context.page_size
        # Query limit+1 to detect has_more without a second query
        detect_limit = limit + 1
        page_num = (offset // limit) + 1

        if filters.search_type == "room":
            page_results = self.room_repo.search(filters, offset=offset, limit=detect_limit)
        elif filters.search_type in ("property", "full", "shared"):
            page_results = self.property_repo.search(filters, offset=offset, limit=detect_limit)
        else:
            return ChatResponse(
                reply=t("SEARCH_TYPE_MISSING", lang),
                response_type="clarification",
                pending_slot="search_type",
                filters=filters,
                suggestions=self.flow.get_slot_suggestions("search_type", lang),
            )

        has_more = len(page_results) > limit
        results = page_results[:limit]

        context.cache_key = cache_key
        if offset == 0:
            context.cached_results = list(results)
        else:
            context.cached_results.extend(list(results))
            # Limit cached results to prevent memory bloat (keep last 100)
            if len(context.cached_results) > 100:
                context.cached_results = context.cached_results[-100:]

        if not results and (offset > 0):
            return ChatResponse(
                reply=t("END_OF_RESULTS", lang),
                response_type="end_of_results",
                filters=filters,
                pagination=PaginationMeta(page=page_num, page_size=limit, has_more=False),
            )

        if not results and offset == 0:
            location_name = filters.city or filters.governorate or ""
            if not location_name:
                location_name = "the available areas" if lang == "en" else "المناطق المتاحة"
            search_type_name = {
                "room": "rooms" if lang == "en" else "أوض",
                "property": "properties" if lang == "en" else "شقق",
                "full": "apartments" if lang == "en" else "شقق كاملة",
                "shared": "shared housing" if lang == "en" else "شقق مشتركة",
            }.get(filters.search_type, "results" if lang == "en" else "نتائج")
            context.push_search(filters, 0)
            return ChatResponse(
                reply=t("NO_RESULTS", lang, type=search_type_name, location=location_name),
                response_type="no_results",
                filters=filters,
                suggestions=self.flow.build_no_results_suggestions(filters, lang),
                pagination=PaginationMeta(page=page_num, page_size=limit, has_more=False),
            )

        if offset == 0:
            if filters.search_type == "room":
                total_count = self.room_repo.count(filters)
            else:
                total_count = self.property_repo.count(filters)
            context.last_results_count = total_count
        else:
            context.last_results_count = len(results)

        ids = [row.get("Id") for row in results if row.get("Id")]
        if filters.search_type == "room":
            context.mark_seen(room_ids=ids)
        else:
            context.mark_seen(property_ids=ids)

        if offset == 0:
            context.push_search(filters, len(results))

        if filters.search_type == "room":
            reply, cards = self.formatter.format_rooms(results, filters, has_more=has_more, page_num=page_num)
        else:
            reply, cards = self.formatter.format_properties(results, filters, has_more=has_more, page_num=page_num)

        return ChatResponse(
            reply=reply,
            response_type="results",
            filters=filters,
            suggestions=self.flow.build_result_suggestions(context, filters, has_more),
            results=cards,
            pagination=PaginationMeta(page=page_num, page_size=limit, has_more=has_more),
        )

    def _filters_hash(self, filters: SearchFilters) -> str:
        data = json.dumps(filters.model_dump(), sort_keys=True, default=str)
        return hashlib.md5(data.encode()).hexdigest()