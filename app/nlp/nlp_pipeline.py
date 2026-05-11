"""
NLPPipeline — المحرك الرئيسي للـ NLP
"""

import re
from typing import Optional
from app.nlp.parsed_message import ParsedMessage, LocationResult, PriceResult
from app.nlp.token_map import TOKEN_MAP
from app.models.search_models import SearchFilters
from app.services.location_service import LocationService
from app.extractors.price_extractor import PriceExtractor
from app.extractors.followup_extractor import FollowUpExtractor
from app.extractors.query_extractor import QueryExtractor
from app.utils.text_normalizer import TextNormalizer
from app.utils.logger import debug_log


class NLPPipeline:

    CONFIDENCE_THRESHOLD = 0.65

    INTENT_KEYWORDS = {
        "room_search": [
            "غرفه", "room", "bedroom", "studio", "سنجل", "single",
            "مشترك", "shared", "roommate", "اوضة", "اوضه", "غرفة",
            "خاص", "private", "فردي", "طلبه", "students", "بنات", "شباب",
        ],
        "property_search": [
            "شقه", "apartment", "flat", "property", "house", "home",
            "villa", "منزل", "عقار", "وحده", "عماره", "مبني",
            "شقة", "شقق", "سكن",
        ],
        "follow_up": [
            "ارخص", "رخيص", "cheap", "اقل", "lower",
            "اغلى", "غالي", "expensive", "اعلى", "higher",
            "تحت", "فوق", "سعر", "price", "budget",
            "مفروش", "مكيف", "wifi", "واي", "انترنت",
            "بلكونه", "حمام", "مطبخ", "غساله", "ثلاجه",
            "قريب", "بعيد", "هادئ", "واسع", "نضيف",
            "بدل", "شيل", "غير", "مش عايز",
        ],
        "show_more": [
            "كمان", "المزيد", "تاني", "more", "next", "show",
            "باقي", "بقية", "كمل", "continue",
        ],
        "go_back": [
            "ارجع", "اللي فات", "قبل", "back", "previous",
            "رجوع", "السابق",
        ],
        "small_talk": [
            "ازيك", "اخبارك", "عامل", "صباح", "مساء", "هاي", "هلو",
            "اهلا", "مرحبا", "شكرا", "ميرسي", "تسلم", "سلام", "باي",
        ],
        "faq": [
            "ازاي", "ايه", "مين", "هل", "عندك", "بتعمل", "فلوس",
            "دفع", "امان", "سعر", "رسوم", "تكلفة", "مصاريف",
        ],
    }

    # Search type detection
    FULL_KEYWORDS = ["كامله", "كاملة", "full", "لوحدي", "لنفسي", "private apartment"]
    SHARED_KEYWORDS = [
        "مشترك", "shared", "roommate", "مع ناس", "مع حد", "سكن مشترك",
        "شقه مشتركه", "شقة مشتركة", "shared apartment", "shared flat",
    ]

    AMENITY_KEYWORDS = {
        "wifi": ["wifi", "wi-fi", "واي", "انترنت", "نت"],
        "furnished": ["مفروش", "furnished"],
        "air_conditioning": ["مكيف", "تكييف", "ac"],
        "balcony": ["بلكونه", "balcony"],
        "private_bathroom": ["حمام_خاص", "private_bathroom", "ensuite"],
        "kitchen": ["مطبخ", "kitchen"],
        "washer": ["غساله", "washer"],
        "refrigerator": ["ثلاجه", "fridge"],
    }

    TENANT_KEYWORDS = {
        "student": ["طلبه", "طلاب", "student", "students", "سكن_طلبه"],
        "worker": ["موظف", "عامل", "worker", "موظفين", "employees"],
    }

    GENDER_KEYWORDS = {
        "male": ["شباب", "ولاد", "boys", "male", "رجاله", "رجالة"],
        "female": ["بنات", "girls", "female", "سيدات", "ladies"],
    }

    SORT_KEYWORDS = {
        "price_low": ["ارخص", "رخيص", "cheap", "اقل", "lower", "سعر_منخفض"],
        "price_high": ["اغلى", "غالي", "expensive", "اعلى", "higher", "سعر_مرتفع"],
    }

    def __init__(self):
        self.location_service = LocationService()
        self.price_extractor = PriceExtractor()
        self.followup_extractor = FollowUpExtractor()
        self.llm_extractor = QueryExtractor()

    def extract(self, message: str, history: str = "", last_search: SearchFilters = None, pending_slot: str = None) -> SearchFilters:
        debug_log("PIPELINE_START", message)

        normalized = TextNormalizer.normalize(message)
        debug_log("NORMALIZED", normalized)

        tokens = self._tokenize(normalized)
        debug_log("TOKENS", tokens)

        parsed = ParsedMessage(
            raw_text=message,
            normalized_text=normalized,
            tokens=tokens,
        )

        self._detect_intent(parsed)
        debug_log("INTENT", f"{parsed.intent} ({parsed.intent_confidence})")

        self._extract_location(parsed)
        debug_log("LOCATION", parsed.location.model_dump() if parsed.location else None)

        self._extract_price(parsed)
        debug_log("PRICE", parsed.price.model_dump() if parsed.price else None)

        self._extract_amenities(parsed)
        debug_log("AMENITIES", parsed.amenities)

        self._extract_tenant_and_gender(parsed)
        debug_log("TENANT/GENDER", f"{parsed.tenant_type}/{parsed.gender}")

        self._extract_sort(parsed)
        debug_log("SORT", parsed.sort_by)

        self._determine_search_type(parsed)
        debug_log("SEARCH_TYPE", parsed.search_type)

        if pending_slot:
            self._handle_slot_reply(parsed, pending_slot)

        parsed.calculate_overall_confidence()
        debug_log("CONFIDENCE", parsed.overall_confidence)

        if parsed.overall_confidence < self.CONFIDENCE_THRESHOLD:
            debug_log("PIPELINE", f"Low confidence ({parsed.overall_confidence:.2f}) → calling LLM")
            parsed = self._llm_fallback(parsed, message, history)
        else:
            parsed.llm_reason = "Rules sufficient — no LLM needed"
            debug_log("PIPELINE", "Rules sufficient — skipping LLM")

        if last_search and (parsed.intent in ("follow_up", "clarification") or pending_slot):
            parsed = self._merge_with_last_search(parsed, last_search)

        filters = parsed.to_search_filters()
        debug_log("FINAL_FILTERS", filters.model_dump())
        return filters

    def _tokenize(self, text: str) -> list[str]:
        words = text.split()
        tokens = []
        i = 0
        while i < len(words):
            word = words[i]
            if i + 1 < len(words):
                two_words = f"{word}_{words[i+1]}"
                if two_words in TOKEN_MAP:
                    tokens.append(TOKEN_MAP[two_words])
                    i += 2
                    continue
            if word in TOKEN_MAP:
                tokens.append(TOKEN_MAP[word])
            else:
                tokens.append(word)
            i += 1
        return tokens

    def _detect_intent(self, parsed: ParsedMessage):
        text = parsed.normalized_text
        tokens = parsed.tokens

        intent_scores = {}

        for intent, keywords in self.INTENT_KEYWORDS.items():
            score = 0
            for kw in keywords:
                if kw in text:
                    score += 1.0
                elif kw in tokens:
                    score += 0.8
            for token in tokens:
                if len(token) >= 3:
                    for kw in keywords:
                        if len(kw) >= 3 and (token in kw or kw in token):
                            score += 0.5
            if score > 0:
                intent_scores[intent] = score

        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            parsed.intent = best_intent
            parsed.intent_confidence = min(intent_scores[best_intent], 1.0)
        else:
            parsed.intent = "invalid"
            parsed.intent_confidence = 0.0

        if parsed.intent == "invalid" and parsed.location:
            parsed.intent = "clarification"
            parsed.intent_confidence = 0.8

    def _extract_location(self, parsed: ParsedMessage):
        loc = self.location_service.detect_location(parsed.raw_text)
        if loc:
            parsed.location = LocationResult(
                type=loc.get("type", ""),
                en=loc.get("en", ""),
                ar="",
                confidence=0.9,
            )
            parsed.location_confidence = 0.9
        else:
            parsed.location_confidence = 0.0

    def _extract_price(self, parsed: ParsedMessage):
        price_data = self.price_extractor.extract(parsed.raw_text)
        if price_data["min_price"] or price_data["max_price"]:
            parsed.price = PriceResult(
                min_price=price_data["min_price"],
                max_price=price_data["max_price"],
                confidence=0.95,
            )
            parsed.price_confidence = 0.95
        else:
            parsed.price_confidence = 0.0

    def _extract_amenities(self, parsed: ParsedMessage):
        text = parsed.normalized_text
        tokens = parsed.tokens

        for amenity, keywords in self.AMENITY_KEYWORDS.items():
            for kw in keywords:
                if kw in text or kw in tokens:
                    negation_words = ["مش", "غير", "بدون", "without", "no", "not", "لأ"]
                    text_parts = text.split()
                    for i, part in enumerate(text_parts):
                        if kw in part:
                            start = max(0, i - 2)
                            context = " ".join(text_parts[start:i])
                            is_negated = any(n in context for n in negation_words)
                            parsed.amenities[amenity] = not is_negated
                            break
                    else:
                        parsed.amenities[amenity] = True
                    break

    def _extract_tenant_and_gender(self, parsed: ParsedMessage):
        text = parsed.normalized_text
        tokens = parsed.tokens

        for ttype, keywords in self.TENANT_KEYWORDS.items():
            for kw in keywords:
                if kw in text or kw in tokens:
                    parsed.tenant_type = ttype
                    break

        for gender, keywords in self.GENDER_KEYWORDS.items():
            for kw in keywords:
                if kw in text or kw in tokens:
                    parsed.gender = gender
                    break

        if "مشترك" in text or "shared" in text or "roommate" in text:
            parsed.shared_room = True
        elif "سنجل" in text or "single" in text or "فردي" in text or "خاص" in text:
            parsed.shared_room = False

    def _extract_sort(self, parsed: ParsedMessage):
        text = parsed.normalized_text
        tokens = parsed.tokens

        followup = self.followup_extractor.extract(parsed.raw_text)
        if followup and followup.sort_by:
            parsed.sort_by = followup.sort_by
            return

        for sort_type, keywords in self.SORT_KEYWORDS.items():
            for kw in keywords:
                if kw in text or kw in tokens:
                    parsed.sort_by = sort_type
                    return

    def _handle_slot_reply(self, parsed: ParsedMessage, pending_slot: str):
        text = parsed.normalized_text
        
        yes_words = ["اه", "ايوه", "نعم", "ياريت", "اكيد", "ايوا"]
        no_words = ["لا", "لأ", "مش", "بدون", "شكرا"]
        any_words = ["اي", "اي حاجة", "مش فارقة", "اي حد", "كله شغال", "مش مهم"]
        
        is_yes = any(text == w for w in yes_words) or any(w in text.split() for w in yes_words)
        is_no = any(text == w for w in no_words) or any(w in text.split() for w in no_words)
        is_any = any(text == w for w in any_words) or any(w in text for w in any_words)

        # If it's a slot reply, confidence is high
        parsed.intent = "clarification"
        parsed.intent_confidence = 1.0

        if pending_slot == "furnished":
            if is_any:
                parsed.amenities["furnished"] = None
            elif is_yes or "مفروش" in text:
                parsed.amenities["furnished"] = True
            elif is_no or "فاضي" in text or "غير مفروش" in text:
                parsed.amenities["furnished"] = False

        elif pending_slot == "tenant_type":
            if is_any:
                parsed.tenant_type = "any"
                parsed.gender = "any"

        elif pending_slot == "price":
            if is_any or is_no:
                parsed.price = None
                
    def _determine_search_type(self, parsed: ParsedMessage):
        """بيحدد نوع البحث"""
        text = parsed.normalized_text

        # Check for "full apartment" keywords FIRST
        for kw in self.FULL_KEYWORDS:
            if kw in text:
                parsed.search_type = "full"
                return

        # Check for shared apartment keywords
        for kw in self.SHARED_KEYWORDS:
            if kw in text:
                parsed.search_type = "shared"
                return

        if parsed.intent == "room_search":
            parsed.search_type = "room"
        elif parsed.intent == "property_search":
            # "شقة" بس = كل الشقق (كاملة + مشتركة)
            parsed.search_type = "property"

    def _llm_fallback(self, parsed: ParsedMessage, message: str, history: str) -> ParsedMessage:
        llm_result = self.llm_extractor.extract(message, history)

        parsed.llm_reason = f"LLM called — confidence was {parsed.overall_confidence:.2f}"

        if llm_result.intent and llm_result.intent != "invalid":
            parsed.intent = llm_result.intent
            parsed.intent_confidence = 0.85

        if llm_result.search_type:
            parsed.search_type = llm_result.search_type

        if llm_result.city:
            parsed.location = LocationResult(type="city", en=llm_result.city, confidence=0.85)
            parsed.location_confidence = 0.85
        elif llm_result.governorate:
            parsed.location = LocationResult(type="governorate", en=llm_result.governorate, confidence=0.85)
            parsed.location_confidence = 0.85

        if llm_result.min_price or llm_result.max_price:
            parsed.price = PriceResult(
                min_price=llm_result.min_price,
                max_price=llm_result.max_price,
                confidence=0.85,
            )
            parsed.price_confidence = 0.85

        for key in ["wifi", "furnished", "balcony", "air_conditioning", "private_bathroom"]:
            val = getattr(llm_result, key)
            if val is not None:
                parsed.amenities[key] = val

        if llm_result.tenant_type:
            parsed.tenant_type = llm_result.tenant_type
        if llm_result.gender:
            parsed.gender = llm_result.gender
        if llm_result.shared_room is not None:
            parsed.shared_room = llm_result.shared_room
        if llm_result.sort_by:
            parsed.sort_by = llm_result.sort_by

        parsed.calculate_overall_confidence()
        parsed.overall_confidence = max(parsed.overall_confidence, 0.75)

        return parsed

    def _merge_with_last_search(self, parsed: ParsedMessage, last_search: SearchFilters) -> ParsedMessage:
        if not parsed.search_type and last_search.search_type:
            parsed.search_type = last_search.search_type

        if not parsed.location and (last_search.city or last_search.governorate):
            if last_search.city:
                parsed.location = LocationResult(type="city", en=last_search.city, confidence=0.8)
            else:
                parsed.location = LocationResult(type="governorate", en=last_search.governorate, confidence=0.8)

        for key in ["wifi", "furnished", "balcony", "air_conditioning", "private_bathroom"]:
            old_val = getattr(last_search, key)
            if key not in parsed.amenities and old_val is not None:
                parsed.amenities[key] = old_val

        if not parsed.tenant_type and last_search.tenant_type:
            parsed.tenant_type = last_search.tenant_type
        if not parsed.gender and last_search.gender:
            parsed.gender = last_search.gender
        if parsed.shared_room is None and last_search.shared_room is not None:
            parsed.shared_room = last_search.shared_room
        if not parsed.sort_by and last_search.sort_by:
            parsed.sort_by = last_search.sort_by

        return parsed
