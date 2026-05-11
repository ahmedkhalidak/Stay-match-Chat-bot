"""
NLPPipeline — المحرك الرئيسي للـ extraction
الترتيب: Normalizer → RuleEngine → (LLM Fallback) → Validator
"""

from app.models.search_models import SearchFilters
from app.extractors.filter_extractor import FilterExtractor
from app.extractors.followup_extractor import FollowUpExtractor
from app.extractors.price_extractor import PriceExtractor
from app.extractors.query_extractor import QueryExtractor
from app.services.intent_service import IntentService
from app.services.location_service import LocationService
from app.utils.logger import debug_log


class NLPPipeline:
    """
    بيشتغل بالترتيب:
    1. Rule Engine (مجاني + سريع)
    2. LLM Enhancer (بس لو محتاجين)
    3. Validator
    """

    def __init__(self):
        self.intent_service = IntentService()
        self.filter_extractor = FilterExtractor()
        self.followup_extractor = FollowUpExtractor()
        self.price_extractor = PriceExtractor()
        self.location_service = LocationService()
        self.llm_extractor = QueryExtractor()

    def extract(self, message: str, history: str = "", last_search: SearchFilters = None) -> SearchFilters:
        """
        يستخرج الفلاتر بأذكى طريقة:
        - Rules first
        - LLM fallback
        """
        debug_log("PIPELINE_START", message)

        # ── 1. Rule Engine ─────────────────────
        rule_result = self._rule_engine(message, last_search)
        confidence = self._calculate_confidence(rule_result, message)
        debug_log("RULE_RESULT", rule_result.model_dump())
        debug_log("RULE_CONFIDENCE", confidence)

        # ── 2. LLM Fallback ────────────────────
        if confidence < 0.6:
            debug_log("PIPELINE", "Low confidence → calling LLM")
            llm_result = self.llm_extractor.extract(message, history)

            # Merge: LLM wins on fields it detected, Rules fill gaps
            final = self._merge_llm_and_rules(rule_result, llm_result)
            debug_log("LLM_RESULT", llm_result.model_dump())
        else:
            final = rule_result

        # ── 3. Post-process ────────────────────
        final = self._post_process(final)
        debug_log("PIPELINE_FINAL", final.model_dump())
        return final

    def _rule_engine(self, message: str, last_search: SearchFilters) -> SearchFilters:
        """الـ Rule Engine بيشتغل بالترتيب"""

        # 1. Intent Detection
        # intent_service.detect_intent needs SessionContext, so we use keyword matching here
        intent = self._detect_intent_simple(message)

        # 2. Follow-up extraction (cheapest first)
        followup = self.followup_extractor.extract(message)
        if followup:
            followup.intent = "follow_up"
            if last_search:
                # Merge with last search
                for field, value in followup.model_dump().items():
                    if value is not None and field != "intent":
                        setattr(last_search, field, value)
                last_search.intent = "follow_up"
                return last_search
            return followup

        # 3. Full filter extraction (keyword-based)
        filters = self.filter_extractor.extract(message)
        filters.intent = intent

        # 4. Price extraction (regex)
        price_data = self.price_extractor.extract(message)
        if price_data["min_price"]:
            filters.min_price = price_data["min_price"]
        if price_data["max_price"]:
            filters.max_price = price_data["max_price"]

        # 5. Location extraction
        loc = self.location_service.detect_location(message)
        if loc:
            if loc["type"] == "city":
                filters.city = loc["en"]
            else:
                filters.governorate = loc["en"]

        return filters

    # Diverse examples for user guidance (Ismailia prioritized)
    _EXAMPLE_CITIES = [
        "الإسماعيلية", "الإسكندرية", "طنطا", "أسوان",
        "القاهرة", "المنصورة", "سوهاج", "الغردقة",
    ]

    def _detect_intent_simple(self, message: str) -> str:
        """Intent detection سريع بالكلمات المفتاحية"""
        msg = message.lower()

        # Small talk
        if any(w in msg for w in ["ازيك", "اخبارك", "عامل ايه", "صباح", "مساء", "هاي", "هلو", "اهلا", "مرحبا"]):
            return "small_talk"

        # Thanks
        if any(w in msg for w in ["شكرا", "ميرسي", "تسلم", "متشكر", "ثانكس"]):
            return "small_talk"

        # Bye
        if any(w in msg for w in ["سلام", "باي", "مع السلامه", "اشوفك"]):
            return "small_talk"

        # FAQ
        if any(w in msg for w in ["ازاي", "ايه هو", "مين", "هل", "عندك", "بتعمل ايه", "فلوس", "دفع", "امان"]):
            return "faq"

        # Show more
        if any(w in msg for w in ["كمان", "المزيد", "تاني", "show more", "more", "next", "عايز أشوف كمان", "باقي"]):
            return "show_more"

        # Go back
        if any(w in msg for w in ["ارجع", "اللي فات", "قبل كده", "back", "previous", "اللي قبله"]):
            return "go_back"

        # Room search
        if any(w in msg for w in ["اوضة", "اوضه", "غرفة", "غرفه", "room", "سنجل", "مشتركة"]):
            return "room_search"

        # Property search
        if any(w in msg for w in ["شقة", "شقه", "شقق", "apartment", "سكن", "عقار"]):
            return "property_search"

        # Follow-up (price sorting)
        if any(w in msg for w in ["ارخص", "اقل", "رخيص", "اغلي", "اعلى", "غالي"]):
            return "follow_up"

        # Follow-up (amenities)
        if any(w in msg for w in ["فيها", "مش عايز", "شيل", "غير", "بدل"]):
            return "follow_up"

        # Location-only
        loc = self.location_service.detect_location(message)
        if loc:
            return "clarification"

        return "invalid"

    def _calculate_confidence(self, filters: SearchFilters, message: str) -> float:
        """بيحسب مدى ثقتنا في الـ Rules"""
        score = 0.0
        msg_len = len(message.strip())

        # Intent detected?
        if filters.intent and filters.intent != "invalid":
            score += 0.3

        # City detected?
        if filters.city or filters.governorate:
            score += 0.2

        # Price detected?
        if filters.min_price or filters.max_price:
            score += 0.15

        # Search type detected?
        if filters.search_type:
            score += 0.15

        # Amenities detected?
        if any([filters.wifi, filters.furnished, filters.balcony, filters.air_conditioning]):
            score += 0.1

        # Tenant type or gender?
        if filters.tenant_type or filters.gender:
            score += 0.1

        # Short messages with intent = higher confidence
        if msg_len < 20 and filters.intent not in ["invalid", "faq"]:
            score += 0.1

        return min(score, 1.0)

    def _merge_llm_and_rules(self, rules: SearchFilters, llm: SearchFilters) -> SearchFilters:
        """LLM wins على الحقول اللي اكتشفها، Rules بتملي الفراغات"""
        merged = rules.model_copy(deep=True)

        for field, value in llm.model_dump().items():
            if field == "intent":
                if value and value != "invalid":
                    merged.intent = value
                continue
            if value is not None:
                setattr(merged, field, value)

        return merged

    def _post_process(self, filters: SearchFilters) -> SearchFilters:
        """تنظيف نهائي"""
        # Swap wrong prices
        if filters.min_price and filters.max_price and filters.min_price > filters.max_price:
            filters.min_price, filters.max_price = filters.max_price, filters.min_price

        # Default sort
        if not filters.sort_by:
            filters.sort_by = "relevance"

        return filters
