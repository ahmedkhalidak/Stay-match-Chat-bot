"""
Search execution and response assembly.
Keeps repository access, pagination, and result formatting out of orchestration.
"""

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

    def execute(
        self,
        filters: SearchFilters,
        context: SessionContext,
    ) -> ChatResponse:
        debug_log("SEARCH_EXECUTOR", f"Executing search - type: {filters.search_type}, city: {filters.city}, governorate: {filters.governorate}")
        cache_key = self._filters_hash(filters)
        
        # Use cursor-based pagination if enabled
        use_cursor = context.use_cursor_pagination
        cursor = context.last_cursor if use_cursor else None
        offset = context.current_offset if not use_cursor else 0
        limit = context.page_size
        page_num = (offset // limit) + 1
        debug_log("SEARCH_EXECUTOR_OFFSET", f"Using offset: {offset}, page_num: {page_num}, cursor_pagination: {use_cursor}")

        if filters.search_type == "room":
            if use_cursor:
                debug_log("SEARCH", f"room cursor={cursor} limit={limit}")
                page_results, next_cursor, has_more = self.room_repo.search_with_cursor(filters, cursor, limit)
            else:
                debug_log("SEARCH", f"room offset={offset} limit={limit}")
                page_results = self.room_repo.search(filters, offset=offset, limit=limit)
                next_page = self.room_repo.search(filters, offset=offset + limit, limit=1)
                has_more = len(next_page) > 0
                next_cursor = None
        elif filters.search_type in ("property", "full", "shared"):
            if use_cursor:
                debug_log("SEARCH", f"{filters.search_type} cursor={cursor} limit={limit}")
                page_results, next_cursor, has_more = self.property_repo.search_with_cursor(filters, cursor, limit)
            else:
                debug_log("SEARCH", f"{filters.search_type} offset={offset} limit={limit}")
                page_results = self.property_repo.search(filters, offset=offset, limit=limit)
                next_page = self.property_repo.search(filters, offset=offset + limit, limit=1)
                has_more = len(next_page) > 0
                next_cursor = None
        else:
            return ChatResponse(
                reply="ابدأ بتحديد إنك عايز أوضة ولا شقة.",
                response_type="clarification",
                pending_slot="search_type",
                filters=filters,
                suggestions=self.flow.get_slot_suggestions("search_type"),
            )

        context.cache_key = cache_key
        if use_cursor:
            context.update_cursor(next_cursor)
        else:
            if offset == 0:
                context.cached_results = list(page_results)
            else:
                context.cached_results.extend(list(page_results))

        if not page_results and (offset > 0 or cursor):
            return ChatResponse(
                reply="دي كانت آخر النتائج المتاحة للبحث ده.",
                response_type="end_of_results",
                filters=filters,
                pagination=PaginationMeta(
                    page=page_num,
                    page_size=limit,
                    has_more=False,
                ),
            )

        if not page_results and offset == 0 and not cursor:
            location_name = filters.city or filters.governorate or "المناطق المتاحة"
            search_type_name = {
                "room": "أوض",
                "property": "شقق",
                "full": "شقق كاملة",
                "shared": "شقق مشتركة",
            }.get(filters.search_type, "نتائج")
            context.push_search(filters, 0)
            return ChatResponse(
                reply=(
                    f"مش لاقي {search_type_name} مناسبة في {location_name} حالياً.\n"
                    "جرّب توسّع المكان أو تغيّر الميزانية."
                ),
                response_type="no_results",
                filters=filters,
                suggestions=self.flow.build_no_results_suggestions(filters),
                pagination=PaginationMeta(
                    page=page_num,
                    page_size=limit,
                    has_more=False,
                ),
            )

        # Get total count for housing_type clarification check
        if offset == 0 and not cursor:
            if filters.search_type == "room":
                total_count = self.room_repo.count(filters)
            else:
                total_count = self.property_repo.count(filters)
            context.last_results_count = total_count
            debug_log("SEARCH_EXECUTOR_COUNT", f"Total results: {total_count}")
        else:
            context.last_results_count = len(page_results)
        
        # Mark seen IDs on every page to prevent duplicates (not just first page)
        ids = [row.get("Id") for row in page_results if row.get("Id")]
        if filters.search_type == "room":
            context.mark_seen(room_ids=ids)
            debug_log("SEARCH_EXECUTOR_SEEN", f"Marked {len(ids)} room IDs as seen, total seen: {len(context.seen_room_ids)}")
        else:
            context.mark_seen(property_ids=ids)
            debug_log("SEARCH_EXECUTOR_SEEN", f"Marked {len(ids)} property IDs as seen, total seen: {len(context.seen_property_ids)}")
        
        if offset == 0 and not cursor:
            context.push_search(filters, len(page_results))

        if filters.search_type == "room":
            reply, cards = self.formatter.format_rooms(
                page_results,
                filters,
                has_more=has_more,
                page_num=page_num,
            )
        else:
            reply, cards = self.formatter.format_properties(
                page_results,
                filters,
                has_more=has_more,
                page_num=page_num,
            )

        return ChatResponse(
            reply=reply,
            response_type="results",
            filters=filters,
            suggestions=self.flow.build_result_suggestions(context, filters, has_more),
            results=cards,
            pagination=PaginationMeta(
                page=page_num,
                page_size=limit,
                has_more=has_more,
            ),
        )

    def _filters_hash(self, filters: SearchFilters) -> str:
        data = json.dumps(filters.model_dump(), sort_keys=True, default=str)
        return hashlib.md5(data.encode()).hexdigest()
