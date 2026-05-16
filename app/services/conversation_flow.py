"""
ConversationFlow - deterministic state management for the chatbot.
The flow keeps the first-search path short, then lets the user refine naturally.
"""

from app.core.session_context import SessionContext
from app.models.response_models import QuickReply
from app.models.search_models import SearchFilters
from app.utils.logger import debug_log
from app.utils.text_normalizer import TextNormalizer


class ConversationFlow:
    ASK_SEARCH_TYPE = (
        "أهلاً بيك في StayMatch.\n"
        "بتدور على إيه؟"
    )

    ASK_LOCATION = (
        "تمام، تحب تدور فين؟\n"
        "اكتب المدينة أو المنطقة، أو قول \"أي مكان\" لو عايز تشوف كل المتاح."
    )

    ASK_PRICE = (
        "ميزانيتك الشهرية تقريباً كام؟\n"
        "مثلاً: \"تحت 5000\" أو \"من 3000 لـ 7000\"، أو قول \"أي سعر\"."
    )

    ANY_LOCATION_PHRASES = {
        "اي مكان",
        "أي مكان",
        "كل مصر",
        "في اي مكان",
        "في أي مكان",
    }
    ANY_PRICE_PHRASES = {
        "اي سعر",
        "أي سعر",
        "مش مهم السعر",
        "السعر مش فارق",
        "بدون ميزانيه",
    }
    ANY_FURNISHED_PHRASES = {
        "اي حاجه",
        "أي حاجة",
        "مش فارقه",
        "مش مهم",
    }
    ANY_TENANT_PHRASES = {
        "اي حد",
        "أي حد",
        "مش فارقه",
        "مش مهم",
    }

    def apply_preferences_to_filters(
        self,
        context: SessionContext,
        filters: SearchFilters,
    ) -> SearchFilters:
        """
        Fill only truly missing values from stored preferences.
        Explicitly skipped slots must stay open instead of being reintroduced.
        """
        p = context.user_preferences
        if not p:
            return filters

        if (
            "location" not in context.skipped_slots
            and not filters.city
            and not filters.governorate
            and p.preferred_location
        ):
            from app.utils.location_mapping import location_mapping

            gov = location_mapping.get_governorate(p.preferred_location)
            if gov and gov.lower() == p.preferred_location.lower():
                filters.governorate = gov
            else:
                filters.city = p.preferred_location

        if "price" not in context.skipped_slots:
            if filters.min_price is None and p.min_budget is not None:
                filters.min_price = p.min_budget
            if filters.max_price is None and p.max_budget is not None:
                filters.max_price = p.max_budget

        if "tenant_type" not in context.skipped_slots:
            if filters.tenant_type is None and p.tenant_type:
                filters.tenant_type = p.tenant_type
            if filters.gender is None and p.gender:
                filters.gender = p.gender

        if "furnished" not in context.skipped_slots and filters.furnished is None:
            if p.furnished is not None:
                filters.furnished = p.furnished

        if filters.wifi is None and p.wifi is not None:
            filters.wifi = p.wifi
        if filters.air_conditioning is None and p.air_conditioning is not None:
            filters.air_conditioning = p.air_conditioning
        if filters.balcony is None and p.balcony is not None:
            filters.balcony = p.balcony
        if filters.private_bathroom is None and p.private_bathroom is not None:
            filters.private_bathroom = p.private_bathroom
        if filters.shared_room is None and p.shared_room is not None:
            filters.shared_room = p.shared_room

        return filters

    def apply_user_overrides(
        self,
        context: SessionContext,
        filters: SearchFilters,
        message: str,
    ) -> SearchFilters:
        """
        Interpret "any" answers as explicit skips, not missing information.
        """
        text = TextNormalizer.normalize(message)

        if self._matches_any(text, self.ANY_LOCATION_PHRASES):
            filters.city = None
            filters.governorate = None
            context.skipped_slots.add("location")
            context.user_preferences.preferred_location = None

        if self._matches_any(text, self.ANY_PRICE_PHRASES):
            filters.min_price = None
            filters.max_price = None
            context.skipped_slots.add("price")
            context.user_preferences.min_budget = None
            context.user_preferences.max_budget = None

        if (
            context.pending_slot == "furnished"
            and self._matches_any(text, self.ANY_FURNISHED_PHRASES)
        ):
            filters.furnished = None
            context.skipped_slots.add("furnished")
            context.user_preferences.furnished = None

        if (
            context.pending_slot == "tenant_type"
            and self._matches_any(text, self.ANY_TENANT_PHRASES)
        ):
            filters.tenant_type = None
            filters.gender = None
            context.skipped_slots.add("tenant_type")
            context.user_preferences.tenant_type = None
            context.user_preferences.gender = None

        return filters

    def sync_skipped_slots(
        self,
        context: SessionContext,
        filters: SearchFilters,
    ):
        """
        A later explicit answer should reopen a previously skipped slot.
        """
        if filters.city or filters.governorate:
            context.skipped_slots.discard("location")
        if filters.min_price is not None or filters.max_price is not None:
            context.skipped_slots.discard("price")
        if filters.furnished is not None:
            context.skipped_slots.discard("furnished")
        if filters.tenant_type is not None or filters.gender is not None:
            context.skipped_slots.discard("tenant_type")

    def get_next_clarification(
        self,
        context: SessionContext,
        filters: SearchFilters,
    ) -> tuple[str | None, str | None]:
        """
        Ask the next highest-value question.
        The first search path intentionally stays short: type -> location -> budget.
        """
        debug_log("FLOW_CHECK", f"turn={context.turn_count}, filters={filters.model_dump()}")

        if not filters.search_type:
            context.last_clarification = "search_type"
            return self.ASK_SEARCH_TYPE, "search_type"

        if (
            not filters.city
            and not filters.governorate
            and "location" not in context.skipped_slots
        ):
            context.last_clarification = "location"
            return self.ASK_LOCATION, "location"

        if (
            filters.min_price is None
            and filters.max_price is None
            and "price" not in context.skipped_slots
            and context.turn_count <= 3
            and context.no_results_count == 0
        ):
            context.last_clarification = "price"
            return self.ASK_PRICE, "price"

        context.last_clarification = None
        return None, None

    def get_slot_suggestions(self, slot: str | None) -> list[QuickReply]:
        suggestions = {
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
                QuickReply(label="تحت 5000", value="تحت 5000"),
                QuickReply(label="3000 - 7000", value="من 3000 لـ 7000"),
                QuickReply(label="أي سعر", value="أي سعر"),
            ],
        }
        return suggestions.get(slot or "", [])

    def build_result_suggestions(
        self,
        context: SessionContext,
        filters: SearchFilters,
        has_more: bool,
    ) -> list[QuickReply]:
        suggestions: list[QuickReply] = []

        if has_more:
            suggestions.append(QuickReply(label="المزيد", value="المزيد"))
        if filters.min_price is None and filters.max_price is None:
            suggestions.append(QuickReply(label="الأرخص", value="أرخص"))
        if filters.furnished is None:
            suggestions.append(QuickReply(label="مفروشة", value="مفروشة"))
        if filters.wifi is None:
            suggestions.append(QuickReply(label="واي فاي", value="فيها واي فاي"))
        if context.total_searches >= 1:
            suggestions.append(QuickReply(label="مكان تاني", value="في الإسكندرية"))

        return suggestions[:4]

    def build_no_results_suggestions(
        self,
        filters: SearchFilters,
    ) -> list[QuickReply]:
        suggestions = [
            QuickReply(label="أي مكان", value="أي مكان"),
            QuickReply(label="تحت 10000", value="تحت 10000"),
        ]
        if filters.city or filters.governorate:
            suggestions.append(QuickReply(label="الإسكندرية", value="في الإسكندرية"))
        return suggestions

    def _matches_any(self, text: str, phrases: set[str]) -> bool:
        normalized_phrases = {
            TextNormalizer.normalize(phrase)
            for phrase in phrases
        }
        return text in normalized_phrases
