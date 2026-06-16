from typing import Optional
from app.models.response_models import QuickReply
from app.models.search_models import SearchFilters
from app.utils.bilingual_responses import t


class SuggestionGenerator:

    @staticmethod
    def _qs(label_value_pairs: list[tuple[str, str]]) -> list[QuickReply]:
        return [QuickReply(label=p[0], value=p[1]) for p in label_value_pairs]

    @staticmethod
    def generate_result_suggestions(
        filters: SearchFilters,
        total_results: int,
        has_more: bool,
        lang: str = "ar",
    ) -> list[QuickReply]:
        suggestions: list[QuickReply] = []

        if total_results > 20:
            suggestions = SuggestionGenerator._qs(t("LARGE_RESULT", lang))
            return suggestions[:4]

        if filters.search_type in ("property", "full"):
            suggestions = SuggestionGenerator._qs(t("APARTMENT_SUGGESTIONS", lang))
        elif filters.search_type == "shared":
            suggestions = SuggestionGenerator._qs(t("SHARED_SUGGESTIONS", lang))
        elif filters.search_type == "room":
            suggestions = SuggestionGenerator._qs(t("ROOM_SUGGESTIONS", lang))
        else:
            suggestions = [
                QuickReply(label=t("LARGE_RESULT", lang)[0][0], value=t("LARGE_RESULT", lang)[0][1]),
            ]

        if has_more and "المزيد" not in [s.value for s in suggestions] and "More" not in [s.label for s in suggestions]:
            suggestions.insert(0, QuickReply(label="More" if lang == "en" else "المزيد", value="المزيد"))

        return suggestions[:4]

    @staticmethod
    def generate_no_results_suggestions(
        filters: SearchFilters,
        lang: str = "ar",
    ) -> list[QuickReply]:
        if filters.min_price is not None or filters.max_price is not None:
            return SuggestionGenerator._qs(t("BUDGET_RECOVERY", lang))
        return SuggestionGenerator._qs(t("NO_RESULTS_RECOVERY", lang))

    @staticmethod
    def generate_clarification_suggestions(
        slot: Optional[str] = None,
        lang: str = "ar",
    ) -> list[QuickReply]:
        if slot:
            return SuggestionGenerator.get_slot_suggestions(slot, lang)
        housing = t("HOUSING_SUGGESTIONS", lang)
        return [
            QuickReply(label=housing[0], value="شقة كاملة" if lang == "ar" else "apartment"),
            QuickReply(label=housing[1], value="غرفة" if lang == "ar" else "room"),
            QuickReply(label=housing[2], value="شقة مشتركة" if lang == "ar" else "shared"),
        ]

    @staticmethod
    def generate_followup_suggestions(
        filters: SearchFilters,
        has_more: bool,
        lang: str = "ar",
    ) -> list[QuickReply]:
        if filters.search_type in ("property", "full"):
            suggestions = SuggestionGenerator._qs(t("FOLLOWUP_APARTMENT", lang))
        elif filters.search_type == "shared":
            suggestions = SuggestionGenerator._qs(t("FOLLOWUP_SHARED", lang))
        elif filters.search_type == "room":
            suggestions = SuggestionGenerator._qs(t("FOLLOWUP_ROOM", lang))
        else:
            suggestions = []

        if has_more and "المزيد" not in [s.value for s in suggestions] and "More" not in [s.label for s in suggestions]:
            suggestions.append(QuickReply(label="More" if lang == "en" else "المزيد", value="المزيد"))

        return suggestions[:4]

    @staticmethod
    def get_slot_suggestions(slot: str | None, lang: str = "ar") -> list[QuickReply]:
        if slot == "search_type":
            labels = t("SEARCH_TYPE_SUGGESTIONS", lang)
            return [
                QuickReply(label=labels[0], value="أوضة" if lang == "ar" else "room"),
                QuickReply(label=labels[1], value="شقة كاملة" if lang == "ar" else "full apartment"),
                QuickReply(label=labels[2], value="شقة مشتركة" if lang == "ar" else "shared housing"),
            ]
        elif slot == "location":
            labels = t("LOCATION_SUGGESTIONS", lang)
            return [
                QuickReply(label=labels[0], value="في القاهرة" if lang == "ar" else "in cairo"),
                QuickReply(label=labels[1], value="في المعادي" if lang == "ar" else "in maadi"),
                QuickReply(label=labels[2], value="في الإسكندرية" if lang == "ar" else "in alexandria"),
                QuickReply(label=labels[3], value="أي مكان" if lang == "ar" else "anywhere"),
            ]
        elif slot == "price":
            labels = t("PRICE_SUGGESTIONS", lang)
            return [
                QuickReply(label=labels[0], value=labels[0] if lang == "en" else "تحت 3000"),
                QuickReply(label=labels[1], value=labels[1] if lang == "en" else "تحت 5000"),
                QuickReply(label=labels[2], value=labels[2] if lang == "en" else "تحت 10000"),
                QuickReply(label=labels[3], value="أي سعر" if lang == "ar" else "any price"),
            ]
        elif slot == "housing_type":
            labels = t("HOUSING_SUGGESTIONS", lang)
            return [
                QuickReply(label=labels[0], value="شقة كاملة" if lang == "ar" else "apartment"),
                QuickReply(label=labels[1], value="غرفة" if lang == "ar" else "room"),
                QuickReply(label=labels[2], value="شقة مشتركة" if lang == "ar" else "shared"),
                QuickReply(label=labels[3], value="اعرض الكل" if lang == "ar" else "show all"),
            ]
        return []
