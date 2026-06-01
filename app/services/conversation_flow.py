from app.core.session_context import SessionContext
from app.models.response_models import QuickReply
from app.models.search_models import SearchFilters
from app.services.suggestion_generator import SuggestionGenerator
from app.utils.logger import debug_log
from app.utils.price_parser import PriceParser
from app.utils.text_normalizer import TextNormalizer
from app.utils.bilingual_responses import t
from app.nlp.lexicon import ANY_HOUSING_TYPE_PHRASES


class ConversationFlow:

    HOUSING_TYPE_RESULT_THRESHOLD = 5

    ROOT_SEARCH_HOUSING_KEYWORDS = {
        "شقة كاملة", "شقه كامله", "شقة", "شقه", "كاملة", "كامله",
        "شقة مشتركة", "شقه مشتركه", "سكن مشترك", "مشترك",
        "غرفة", "غرفه", "غرف", "اوضة", "اوضه",
        "room", "rooms", "apartment", "flat", "shared",
        "apartment", "studio", "bedroom",
    }

    ANY_LOCATION_PHRASES_AR = {
        "اي مكان", "أي مكان", "كل مصر", "في اي مكان", "في أي مكان",
    }
    ANY_LOCATION_PHRASES_EN = {
        "anywhere", "any place", "all egypt", "everywhere",
    }
    ANY_PRICE_PHRASES_AR = {
        "اي سعر", "أي سعر", "مش مهم السعر", "السعر مش فارق", "بدون ميزانيه",
    }
    ANY_PRICE_PHRASES_EN = {
        "any price", "no budget", "any budget", "price doesn't matter", "doesn't matter",
    }

    @staticmethod
    def _is_root_search_housing_type(message: str) -> bool:
        normalized = TextNormalizer.normalize(message)
        for keyword in ConversationFlow.ROOT_SEARCH_HOUSING_KEYWORDS:
            if keyword in normalized:
                return True
        return False

    @staticmethod
    def _reset_secondary_filters(filters: SearchFilters, preserve_location: bool = True) -> SearchFilters:
        filters.tenant_type = None
        filters.gender = None
        filters.furnished = None
        filters.wifi = None
        filters.private_bathroom = None
        filters.balcony = None
        filters.air_conditioning = None
        filters.min_price = None
        filters.max_price = None
        filters.sort_by = None
        filters.shared_room = None
        return filters

    def apply_preferences_to_filters(
        self, context: SessionContext, filters: SearchFilters, message: str = None
    ) -> SearchFilters:
        p = context.user_preferences
        if not p:
            return filters

        if message and filters.housing_type and self._is_root_search_housing_type(message):
            debug_log("ROOT_SEARCH_DETECTED", f"Explicit housing type: {filters.housing_type}")
            self._reset_secondary_filters(filters, preserve_location=True)
            p.tenant_type = None
            p.gender = None
            p.furnished = None
            p.wifi = None
            p.private_bathroom = None
            p.balcony = None
            p.air_conditioning = None
            p.min_budget = None
            p.max_budget = None
            p.shared_room = None

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
            if filters.min_price is not None or filters.max_price is not None:
                filters.min_price, filters.max_price = PriceParser.apply_price_override(
                    current_min=p.min_budget,
                    current_max=p.max_budget,
                    new_min=filters.min_price,
                    new_max=filters.max_price,
                )
                p.min_budget = filters.min_price
                p.max_budget = filters.max_price
            else:
                if p.min_budget is not None:
                    filters.min_price = p.min_budget
                if p.max_budget is not None:
                    filters.max_price = p.max_budget

        if "tenant_type" not in context.skipped_slots:
            if filters.tenant_type is None and p.tenant_type:
                filters.tenant_type = p.tenant_type
            if filters.gender is None and p.gender:
                filters.gender = p.gender

        if "furnished" not in context.skipped_slots and filters.furnished is None:
            if p.furnished is not None:
                filters.furnished = p.furnished

        for attr in ["wifi", "air_conditioning", "balcony", "private_bathroom", "shared_room"]:
            if getattr(filters, attr) is None and getattr(p, attr) is not None:
                setattr(filters, attr, getattr(p, attr))

        if filters.housing_type is None and p.housing_type:
            filters.housing_type = p.housing_type

        return filters

    def apply_user_overrides(self, context: SessionContext, filters: SearchFilters, message: str) -> SearchFilters:
        text = TextNormalizer.normalize(message)

        if text in self.ANY_LOCATION_PHRASES_AR or text in self.ANY_LOCATION_PHRASES_EN:
            filters.city = None
            filters.governorate = None
            context.skipped_slots.add("location")
            context.user_preferences.preferred_location = None

        if text in self.ANY_PRICE_PHRASES_AR or text in self.ANY_PRICE_PHRASES_EN:
            filters.min_price = None
            filters.max_price = None
            context.skipped_slots.add("price")
            context.user_preferences.min_budget = None
            context.user_preferences.max_budget = None

        if context.pending_slot == "furnished":
            any_furnished = {"اي حاجه", "أي حاجة", "مش فارقه", "مش مهم", "any", "anything", "doesn't matter"}
            if text in any_furnished:
                filters.furnished = None
                context.skipped_slots.add("furnished")
                context.user_preferences.furnished = None

        if context.pending_slot == "tenant_type":
            any_tenant = {"اي حد", "أي حد", "مش فارقه", "مش مهم", "anyone", "any", "doesn't matter"}
            if text in any_tenant:
                filters.tenant_type = None
                filters.gender = None
                context.skipped_slots.add("tenant_type")
                context.user_preferences.tenant_type = None
                context.user_preferences.gender = None

        if context.pending_slot == "housing_type":
            if text in ANY_HOUSING_TYPE_PHRASES or text in {"any", "all", "show all", "all types", "everything"}:
                filters.housing_type = "any"
                context.skipped_slots.add("housing_type")
                context.user_preferences.housing_type = "any"

        return filters

    def sync_skipped_slots(self, context: SessionContext, filters: SearchFilters):
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
        self, context: SessionContext, filters: SearchFilters, result_count: int
    ) -> bool:
        if filters.housing_type:
            return False
        if "housing_type" in context.skipped_slots:
            return False
        if result_count < self.HOUSING_TYPE_RESULT_THRESHOLD:
            return False
        return True

    def get_housing_type_clarification(
        self, context: SessionContext, filters: SearchFilters, result_count: int, location_name: str = ""
    ) -> tuple[str, str]:
        location_text = location_name or filters.city or filters.governorate or ""
        if location_name:
            display_location = location_name
        else:
            display_location = filters.city or filters.governorate or ""
        lang = context.language
        if not display_location:
            display_location = "the available areas" if lang == "en" else "المناطق المتاحة"
        clarification = t("ASK_HOUSING_TYPE", lang, count=result_count, location=display_location)
        return clarification, "housing_type"

    def get_next_clarification(self, context: SessionContext, filters: SearchFilters) -> tuple[str | None, str | None]:
        lang = context.language

        if not filters.search_type:
            context.last_clarification = "search_type"
            return t("ASK_SEARCH_TYPE", lang), "search_type"

        if (
            not filters.city
            and not filters.governorate
            and "location" not in context.skipped_slots
        ):
            context.last_clarification = "location"
            return t("ASK_LOCATION", lang), "location"

        if (
            filters.min_price is None
            and filters.max_price is None
            and "price" not in context.skipped_slots
            and context.turn_count <= 3
            and context.no_results_count == 0
        ):
            context.last_clarification = "price"
            return t("ASK_PRICE", lang), "price"

        context.last_clarification = None
        return None, None

    def get_slot_suggestions(self, slot: str | None, lang: str = "ar") -> list[QuickReply]:
        return SuggestionGenerator.get_slot_suggestions(slot, lang)

    def build_result_suggestions(self, context: SessionContext, filters: SearchFilters, has_more: bool) -> list[QuickReply]:
        total_results = context.last_results_count
        return SuggestionGenerator.generate_result_suggestions(
            filters=filters,
            total_results=total_results,
            has_more=has_more,
            lang=context.language,
        )

    def build_no_results_suggestions(self, filters: SearchFilters, lang: str = "ar") -> list[QuickReply]:
        return SuggestionGenerator.generate_no_results_suggestions(filters, lang)

    def _matches_any(self, text: str, phrases: set[str]) -> bool:
        return TextNormalizer.normalize(text) in {TextNormalizer.normalize(p) for p in phrases}