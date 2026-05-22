"""
Smart Dynamic Suggestions Generator.
Provides contextual quick-action suggestions based on search context and results.
"""

from typing import Optional
from app.core.session_context import SessionContext
from app.models.response_models import QuickReply
from app.models.search_models import SearchFilters


class SuggestionGenerator:
    """
    Generates smart, contextual suggestions for chatbot interactions.
    Follows strict rules for suggestion relevance and quantity (max 4).
    """

    # Search-type specific suggestions for results
    APARTMENT_SUGGESTIONS = [
        QuickReply(label="الأرخص", value="الأرخص"),
        QuickReply(label="مفروشة", value="مفروشة"),
        QuickReply(label="فيها واي فاي", value="فيها واي فاي"),
        QuickReply(label="المزيد", value="المزيد"),
    ]

    SHARED_HOUSING_SUGGESTIONS = [
        QuickReply(label="للطلاب", value="للطلاب"),
        QuickReply(label="للبنات", value="للبنات"),
        QuickReply(label="الأرخص", value="الأرخص"),
        QuickReply(label="المزيد", value="المزيد"),
    ]

    ROOM_SUGGESTIONS = [
        QuickReply(label="حمام خاص", value="حمام خاص"),
        QuickReply(label="مفروشة", value="مفروشة"),
        QuickReply(label="غرفة خاصة", value="غرفة خاصة"),
        QuickReply(label="المزيد", value="المزيد"),
    ]

    # Narrowing filters for large result sets (>20)
    LARGE_RESULT_SUGGESTIONS = [
        QuickReply(label="الأرخص", value="الأرخص"),
        QuickReply(label="الأحدث", value="الأحدث"),
        QuickReply(label="مفروشة", value="مفروشة"),
        QuickReply(label="تحت 10000", value="تحت 10000"),
    ]

    # Expansion suggestions for small result sets (<=5)
    SMALL_RESULT_SUGGESTIONS = [
        QuickReply(label="أي مكان", value="أي مكان"),
        QuickReply(label="بدون حد للسعر", value="بدون حد للسعر"),
        QuickReply(label="شقة كاملة", value="شقة كاملة"),
        QuickReply(label="سكن مشترك", value="سكن مشترك"),
    ]

    # Recovery suggestions for no results
    NO_RESULTS_SUGGESTIONS = [
        QuickReply(label="أي مكان", value="أي مكان"),
        QuickReply(label="بدون حد للسعر", value="بدون حد للسعر"),
        QuickReply(label="شقة كاملة", value="شقة كاملة"),
        QuickReply(label="سكن مشترك", value="سكن مشترك"),
    ]

    # Clarification buttons for ambiguous intent
    CLARIFICATION_SUGGESTIONS = [
        QuickReply(label="🏠 شقة كاملة", value="شقة كاملة"),
        QuickReply(label="👥 سكن مشترك", value="شقة مشتركة"),
        QuickReply(label="🚪 غرفة", value="غرفة"),
    ]

    # Follow-up filters after specific search types
    FOLLOWUP_APARTMENT = [
        QuickReply(label="الأرخص", value="الأرخص"),
        QuickReply(label="الأحدث", value="الأحدث"),
        QuickReply(label="مفروشة", value="مفروشة"),
        QuickReply(label="المزيد", value="المزيد"),
    ]

    FOLLOWUP_SHARED = [
        QuickReply(label="للطلاب", value="للطلاب"),
        QuickReply(label="للبنات", value="للبنات"),
        QuickReply(label="الأرخص", value="الأرخص"),
        QuickReply(label="المزيد", value="المزيد"),
    ]

    FOLLOWUP_ROOM = [
        QuickReply(label="حمام خاص", value="حمام خاص"),
        QuickReply(label="مفروشة", value="مفروشة"),
        QuickReply(label="غرفة خاصة", value="غرفة خاصة"),
        QuickReply(label="المزيد", value="المزيد"),
    ]

    # Slot-based suggestions for clarification flow
    SLOT_SUGGESTIONS = {
        "search_type": [
            QuickReply(label="أوضة", value="أوضة"),
            QuickReply(label="شقة كاملة", value="شقة كاملة"),
            QuickReply(label="شقة مشتركة", value="شقة مشتركة"),
        ],
        "location": [
            QuickReply(label="المعادي", value="في المعادي"),
            QuickReply(label="الإسكندرية", value="في الإسكندرية"),
            QuickReply(label="أي مكان", value="أي مكان"),
        ],
        "price": [
            QuickReply(label="تحت 3000", value="تحت 3000"),
            QuickReply(label="تحت 5000", value="تحت 5000"),
            QuickReply(label="تحت 10000", value="تحت 10000"),
            QuickReply(label="أي سعر", value="أي سعر"),
        ],
        "housing_type": [
            QuickReply(label="🏠 شقة كاملة", value="شقة كاملة"),
            QuickReply(label="🚪 غرفة", value="غرفة"),
            QuickReply(label="👥 سكن مشترك", value="سكن مشترك"),
            QuickReply(label="اعرض الكل", value="اعرض الكل"),
        ],
    }

    # RULE 11: Budget quick suggestions after search results
    BUDGET_SUGGESTIONS = [
        QuickReply(label="تحت 3000", value="تحت 3000"),
        QuickReply(label="تحت 5000", value="تحت 5000"),
        QuickReply(label="تحت 10000", value="تحت 10000"),
        QuickReply(label="الأرخص", value="الأرخص"),
    ]

    @staticmethod
    def generate_result_suggestions(
        filters: SearchFilters,
        total_results: int,
        has_more: bool,
    ) -> list[QuickReply]:
        """
        Generate contextual suggestions based on search results.
        
        RULE 1: Search-type aware suggestions
        RULE 2: Large result set (>20) - prioritize narrowing filters
        RULE 3: Small result set (<=5) - suggest expanding search
        RULE 6: Follow-up filters based on search type
        """
        suggestions: list[QuickReply] = []

        # RULE 2: Large result set - prioritize narrowing filters
        if total_results > 20:
            suggestions = SuggestionGenerator.LARGE_RESULT_SUGGESTIONS.copy()
            return suggestions[:4]

        # RULE 3: Small result set - suggest expanding search
        if total_results <= 5:
            suggestions = SuggestionGenerator.SMALL_RESULT_SUGGESTIONS.copy()
            return suggestions[:4]

        # RULE 1 & 6: Search-type aware suggestions
        if filters.search_type in ("property", "full"):
            suggestions = SuggestionGenerator.APARTMENT_SUGGESTIONS.copy()
        elif filters.search_type == "shared":
            suggestions = SuggestionGenerator.SHARED_HOUSING_SUGGESTIONS.copy()
        elif filters.search_type == "room":
            suggestions = SuggestionGenerator.ROOM_SUGGESTIONS.copy()
        else:
            # Default fallback
            suggestions = [
                QuickReply(label="الأرخص", value="الأرخص"),
                QuickReply(label="مفروشة", value="مفروشة"),
            ]

        # Ensure "المزيد" is included if there are more results
        if has_more and "المزيد" not in [s.value for s in suggestions]:
            suggestions.append(QuickReply(label="المزيد", value="المزيد"))

        return suggestions[:4]

    @staticmethod
    def generate_no_results_suggestions(
        filters: SearchFilters,
    ) -> list[QuickReply]:
        """
        Generate recovery suggestions when no results are found.
        
        RULE 4: No results recovery buttons
        RULE 10: Budget-specific recovery when budget is too restrictive
        """
        # If budget is set and restrictive, suggest budget recovery
        if filters.min_price is not None or filters.max_price is not None:
            budget_suggestions = [
                QuickReply(label="حتى 7000", value="تحت 7000"),
                QuickReply(label="أي سعر", value="بدون حد للسعر"),
                QuickReply(label="سكن مشترك", value="شقة مشتركة"),
                QuickReply(label="غرفة", value="غرفة"),
            ]
            return budget_suggestions[:4]
        
        return SuggestionGenerator.NO_RESULTS_SUGGESTIONS[:4]

    @staticmethod
    def generate_clarification_suggestions(
        slot: Optional[str] = None,
    ) -> list[QuickReply]:
        """
        Generate clarification suggestions for ambiguous intent.
        
        RULE 5: Clarification flow buttons
        """
        if slot:
            return SuggestionGenerator.SLOT_SUGGESTIONS.get(slot or "", [])[:4]
        
        # Default clarification for ambiguous housing type intent
        return SuggestionGenerator.CLARIFICATION_SUGGESTIONS[:4]

    @staticmethod
    def generate_followup_suggestions(
        filters: SearchFilters,
        has_more: bool,
    ) -> list[QuickReply]:
        """
        Generate follow-up filter suggestions after search results.
        
        RULE 6: Follow-up filters based on search type
        """
        suggestions: list[QuickReply] = []

        if filters.search_type in ("property", "full"):
            suggestions = SuggestionGenerator.FOLLOWUP_APARTMENT.copy()
        elif filters.search_type == "shared":
            suggestions = SuggestionGenerator.FOLLOWUP_SHARED.copy()
        elif filters.search_type == "room":
            suggestions = SuggestionGenerator.FOLLOWUP_ROOM.copy()
        else:
            # Default fallback
            suggestions = [
                QuickReply(label="الأرخص", value="الأرخص"),
                QuickReply(label="مفروشة", value="مفروشة"),
            ]

        # Ensure "المزيد" is included if there are more results
        if has_more and "المزيد" not in [s.value for s in suggestions]:
            suggestions.append(QuickReply(label="المزيد", value="المزيد"))

        return suggestions[:4]

    @staticmethod
    def get_slot_suggestions(slot: str | None) -> list[QuickReply]:
        """
        Get suggestions for a specific clarification slot.
        
        RULE 7: UX Rules - use buttons instead of questions
        """
        return SuggestionGenerator.SLOT_SUGGESTIONS.get(slot or "", [])[:4]
