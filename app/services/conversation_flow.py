"""
ConversationFlow - deterministic state management for the chatbot.
The flow keeps the first-search path short, then lets the user refine naturally.
"""

from app.core.session_context import SessionContext
from app.models.response_models import QuickReply
from app.models.search_models import SearchFilters
from app.utils.logger import debug_log
from app.utils.text_normalizer import TextNormalizer
from app.nlp.lexicon import ANY_HOUSING_TYPE_PHRASES


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

    # Housing type clarification threshold
    HOUSING_TYPE_RESULT_THRESHOLD = 5  # Ask for clarification if > 5 results

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
            from app.utils.logger import debug_log
            debug_log("PRICE_PARSED", f"min_price={filters.min_price}, max_price={filters.max_price}")
            debug_log("PREVIOUS_PRICE_FILTERS", f"min_budget={p.min_budget}, max_budget={p.max_budget}")
            
            # FIX: When user explicitly sets a new price constraint, clear conflicting previous price filters
            # Example: User says "ازيد من 5000" (min_price=5000, max_price=None)
            # Should NOT inherit previous max_price=5000 from "اقل من 5000"
            if filters.min_price is not None or filters.max_price is not None:
                # User explicitly set a price constraint - don't inherit from preferences
                # This prevents conflicting filters like min_price=5000 AND max_price=5000
                debug_log("PRICE_OVERRIDE_DETECTED", "User explicitly set price constraint - not inheriting from preferences")
                pass
            else:
                # No explicit price constraint - inherit from preferences
                if p.min_budget is not None:
                    filters.min_price = p.min_budget
                if p.max_budget is not None:
                    filters.max_price = p.max_budget
                debug_log("PRICE_FILTERS_AFTER_MERGE", f"Inherited from preferences: min_price={filters.min_price}, max_price={filters.max_price}")
            
            debug_log("FINAL_PRICE_FILTERS", f"min_price={filters.min_price}, max_price={filters.max_price}")

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

        if filters.housing_type is None and p.housing_type:
            filters.housing_type = p.housing_type

        from app.utils.logger import debug_log
        debug_log("PREFERENCES_AFTER_MERGE", filters.model_dump())
        
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

        if (
            context.pending_slot == "housing_type"
            and self._matches_any(text, ANY_HOUSING_TYPE_PHRASES)
        ):
            filters.housing_type = "any"
            context.skipped_slots.add("housing_type")
            context.user_preferences.housing_type = "any"

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
        if filters.housing_type is not None:
            context.skipped_slots.discard("housing_type")

    def should_ask_housing_type_clarification(
        self,
        context: SessionContext,
        filters: SearchFilters,
        result_count: int,
    ) -> bool:
        """
        Determine if we should ask for housing_type clarification.
        Only ask when:
        - housing_type is unknown
        - AND search result count is large (>= threshold)
        - AND housing_type hasn't been explicitly skipped
        """
        if filters.housing_type:
            return False  # Already specified

        if "housing_type" in context.skipped_slots:
            return False  # User explicitly skipped

        if result_count < self.HOUSING_TYPE_RESULT_THRESHOLD:
            return False  # Results are manageable, no need to ask

        return True

    def get_housing_type_clarification(
        self,
        context: SessionContext,
        filters: SearchFilters,
        result_count: int,
        location_name: str = "",
    ) -> tuple[str, str]:
        """
        Generate housing type clarification message when result count is large.
        """
        location_text = location_name or filters.city or filters.governorate or "المناطق المتاحة"
        clarification = (
            f"لقيت {result_count} نتيجة في {location_text}.\n\n"
            "تفضل:\n"
            "🏠 شقة كاملة\n"
            "🚪 غرفة\n"
            "👥 سكن مشترك\n\n"
            "أو اكتب اعرض الكل"
        )
        return clarification, "housing_type"

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
            "housing_type": [
                QuickReply(label="🏠 شقة كاملة", value="شقة كاملة"),
                QuickReply(label="🚪 غرفة", value="غرفة"),
                QuickReply(label="👥 سكن مشترك", value="سكن مشترك"),
                QuickReply(label="اعرض الكل", value="اعرض الكل"),
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
