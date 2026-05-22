"""
NLPPipeline — المحرك الرئيسي للـ NLP
"""

from app.nlp.parsed_message import ParsedMessage, LocationResult, PriceResult
from app.nlp.token_map import TOKEN_MAP
from app.nlp.lexicon import (
    AMENITY_KEYWORDS,
    FULL_KEYWORDS,
    GENDER_KEYWORDS,
    INTENT_KEYWORDS,
    NEGATION_WORDS,
    PROPERTY_NOUNS,
    ROOM_NOUNS,
    SEARCH_TYPE_BLOCKED_INTENTS,
    SHARED_KEYWORDS,
    SLOT_REPLY_ANY_WORDS,
    SLOT_REPLY_NO_WORDS,
    SLOT_REPLY_YES_WORDS,
    SORT_KEYWORDS,
    TENANT_KEYWORDS,
)
from app.models.search_models import SearchFilters
from app.services.location_service import LocationService
from app.extractors.price_extractor import PriceExtractor
from app.extractors.followup_extractor import FollowUpExtractor
from app.extractors.query_extractor import QueryExtractor
from app.utils.text_normalizer import TextNormalizer
from app.utils.logger import debug_log
from app.validators.filter_validator import FilterValidator


class NLPPipeline:

    CONFIDENCE_THRESHOLD = 0.65

    def __init__(self):
        self.location_service = LocationService()
        self.price_extractor = PriceExtractor()
        self.followup_extractor = FollowUpExtractor()
        self.llm_extractor = QueryExtractor()
        self.validator = FilterValidator()

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

        self._extract_location(parsed, last_search)
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

        self._promote_entity_only_messages(parsed, last_search, pending_slot)

        parsed.calculate_overall_confidence()
        debug_log("CONFIDENCE", parsed.overall_confidence)

        if parsed.overall_confidence < self.CONFIDENCE_THRESHOLD:
            debug_log("PIPELINE", f"Low confidence ({parsed.overall_confidence:.2f}) → calling LLM")
            parsed = self._llm_fallback(parsed, message, history)
        else:
            parsed.llm_reason = "Rules sufficient — no LLM needed"
            debug_log("PIPELINE", "Rules sufficient — skipping LLM")

        if last_search and (parsed.intent in ("follow_up", "clarification", "remove_filter") or pending_slot):
            parsed = self._merge_with_last_search(parsed, last_search)

        filters = self.validator.validate(parsed.to_search_filters())
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
        words = set(text.split())
        tokens = set(parsed.tokens)

        intent_scores = {}

        for intent, keywords in INTENT_KEYWORDS.items():
            score = 0
            for kw in keywords:
                normalized_kw = TextNormalizer.normalize(kw)
                token_kw = normalized_kw.replace(" ", "_")

                if " " in normalized_kw and normalized_kw in text:
                    score += 1.0
                elif normalized_kw in words:
                    score += 1.0
                elif normalized_kw in tokens or token_kw in tokens:
                    score += 0.8
            if score > 0:
                intent_scores[intent] = score

        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            parsed.intent = best_intent
            parsed.intent_confidence = min(intent_scores[best_intent], 1.0)
        else:
            parsed.intent = "invalid"
            parsed.intent_confidence = 0.0

    def _extract_location(self, parsed: ParsedMessage, last_search: SearchFilters = None):
        loc = None
        if " بدل " in f" {parsed.normalized_text} ":
            replacement_text = parsed.normalized_text.split(" بدل ", 1)[0]
            loc = self.location_service.detect_location(replacement_text)

        if not loc:
            loc = self.location_service.detect_location(parsed.raw_text)
        
        # If no location detected in current message, use location from last_search
        if not loc and last_search:
            if last_search.city:
                loc = {"type": "city", "en": last_search.city}
                debug_log("LOCATION_FROM_LAST", f"Using city from last_search: {last_search.city}")
            elif last_search.governorate:
                loc = {"type": "governorate", "en": last_search.governorate}
                debug_log("LOCATION_FROM_LAST", f"Using governorate from last_search: {last_search.governorate}")
        
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
        text_parts = text.split()
        tokens = parsed.tokens
        for amenity, keywords in AMENITY_KEYWORDS.items():
            match_indexes = [
                index
                for index, token in enumerate(tokens)
                if token in keywords
            ]

            if not match_indexes:
                for index, part in enumerate(text_parts):
                    if any(keyword in part for keyword in keywords):
                        match_indexes.append(index)
                        break

            if not match_indexes:
                continue

            index = match_indexes[0]
            scan_terms = tokens if index < len(tokens) else text_parts
            start = max(0, index - 3)
            context = scan_terms[start:index]
            parsed.amenities[amenity] = not any(
                term in NEGATION_WORDS
                for term in context
            )

    def _extract_tenant_and_gender(self, parsed: ParsedMessage):
        text = parsed.normalized_text
        tokens = parsed.tokens

        for ttype, keywords in TENANT_KEYWORDS.items():
            for kw in keywords:
                if kw in text or kw in tokens:
                    parsed.tenant_type = ttype
                    break

        for gender, keywords in GENDER_KEYWORDS.items():
            for kw in keywords:
                if kw in text or kw in tokens:
                    parsed.gender = gender
                    break

        if "مشترك" in text or "shared" in text or "roommate" in text:
            parsed.shared_room = True
        elif (
            "سنجل" in text
            or "single" in text
            or "فردي" in text
            or "اوضه خاصه" in text
            or "اوضة خاصة" in text
            or "غرفه خاصه" in text
            or "غرفة خاصة" in text
        ):
            parsed.shared_room = False

    def _extract_sort(self, parsed: ParsedMessage):
        words = set(parsed.normalized_text.split())
        tokens = set(parsed.tokens)

        followup = self.followup_extractor.extract(parsed.raw_text)
        if followup and followup.sort_by:
            parsed.sort_by = followup.sort_by
            return

        for sort_type, keywords in SORT_KEYWORDS.items():
            for kw in keywords:
                if kw in words or kw in tokens:
                    parsed.sort_by = sort_type
                    return

    def _handle_slot_reply(self, parsed: ParsedMessage, pending_slot: str):
        text = parsed.normalized_text
        
        is_yes = any(text == word for word in SLOT_REPLY_YES_WORDS) or any(
            word in text.split()
            for word in SLOT_REPLY_YES_WORDS
        )
        is_no = any(text == word for word in SLOT_REPLY_NO_WORDS) or any(
            word in text.split()
            for word in SLOT_REPLY_NO_WORDS
        )
        is_any = any(text == word for word in SLOT_REPLY_ANY_WORDS) or any(
            word in text
            for word in SLOT_REPLY_ANY_WORDS
        )

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
                parsed.tenant_type = None
                parsed.gender = None

        elif pending_slot == "price":
            if is_any or is_no:
                parsed.price = None
                
    def _determine_search_type(self, parsed: ParsedMessage):
        """بيحدد نوع البحث"""
        text = parsed.normalized_text

        has_room_noun = any(
            token in text or token in parsed.tokens
            for token in ROOM_NOUNS
        )
        has_property_noun = any(
            token in text or token in parsed.tokens
            for token in PROPERTY_NOUNS
        )

        if has_room_noun:
            parsed.search_type = "room"
            if parsed.intent not in SEARCH_TYPE_BLOCKED_INTENTS:
                parsed.intent = "room_search"
                parsed.intent_confidence = 1.0
            return

        if has_property_noun:
            if any(keyword in text for keyword in FULL_KEYWORDS):
                parsed.search_type = "full"
            elif any(keyword in text for keyword in SHARED_KEYWORDS):
                parsed.search_type = "shared"
            else:
                parsed.search_type = "property"
            if parsed.intent not in SEARCH_TYPE_BLOCKED_INTENTS:
                parsed.intent = "property_search"
                parsed.intent_confidence = 1.0
            return

        if parsed.intent == "property_search":
            parsed.search_type = "property"

    def _promote_entity_only_messages(
        self,
        parsed: ParsedMessage,
        last_search: SearchFilters | None,
        pending_slot: str | None,
    ):
        if pending_slot:
            parsed.intent = "clarification"
            parsed.intent_confidence = 1.0
            return

        if parsed.intent != "invalid":
            return

        if parsed.location:
            parsed.intent = "follow_up" if " بدل " in f" {parsed.normalized_text} " else "clarification"
            parsed.intent_confidence = 0.85
            return

        if last_search and (
            parsed.price
            or parsed.amenities
            or parsed.tenant_type
            or parsed.gender
            or parsed.shared_room is not None
            or parsed.sort_by
        ):
            parsed.intent = "follow_up"
            parsed.intent_confidence = 0.85

    def _llm_fallback(self, parsed: ParsedMessage, message: str, history: str) -> ParsedMessage:
        debug_log("LLM_FALLBACK", f"Calling LLM - confidence was {parsed.overall_confidence:.2f}")
        debug_log("LLM_INPUT", f"Message: {message[:100]}...")
        
        llm_result = self.llm_extractor.extract(message, history)
        
        debug_log("LLM_OUTPUT", f"Intent: {llm_result.intent}, City: {llm_result.city}, Governorate: {llm_result.governorate}, SearchType: {llm_result.search_type}")

        parsed.llm_reason = f"LLM called — confidence was {parsed.overall_confidence:.2f}"

        if parsed.intent == "invalid" and llm_result.intent and llm_result.intent != "invalid":
            parsed.intent = llm_result.intent
            parsed.intent_confidence = 0.85

        if not parsed.search_type and llm_result.search_type:
            parsed.search_type = llm_result.search_type

        if not parsed.location and llm_result.city:
            parsed.location = LocationResult(type="city", en=llm_result.city, confidence=0.85)
            parsed.location_confidence = 0.85
        elif not parsed.location and llm_result.governorate:
            parsed.location = LocationResult(type="governorate", en=llm_result.governorate, confidence=0.85)
            parsed.location_confidence = 0.85

        if not parsed.price and (llm_result.min_price or llm_result.max_price):
            parsed.price = PriceResult(
                min_price=llm_result.min_price,
                max_price=llm_result.max_price,
                confidence=0.85,
            )
            parsed.price_confidence = 0.85

        for key in ["wifi", "furnished", "balcony", "air_conditioning", "private_bathroom"]:
            val = getattr(llm_result, key)
            if key not in parsed.amenities and val is not None:
                parsed.amenities[key] = val

        if not parsed.tenant_type and llm_result.tenant_type:
            parsed.tenant_type = llm_result.tenant_type
        if not parsed.gender and llm_result.gender:
            parsed.gender = llm_result.gender
        if parsed.shared_room is None and llm_result.shared_room is not None:
            parsed.shared_room = llm_result.shared_room
        if not parsed.sort_by and llm_result.sort_by:
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

        if not parsed.price and (last_search.min_price is not None or last_search.max_price is not None):
            parsed.price = PriceResult(
                min_price=last_search.min_price,
                max_price=last_search.max_price,
                confidence=0.8,
            )

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
