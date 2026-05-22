import json
import difflib
import re
from pathlib import Path
from app.utils.logger import debug_log
from app.utils.text_normalizer import TextNormalizer


class LocationService:

    def __init__(self):
        file_path = (
            Path(__file__).resolve().parent.parent
            / "data"
            / "locations.json"
        )
        with open(file_path, "r", encoding="utf-8-sig") as f:
            self.locations = json.load(f)

        self.all_locations: list[str] = []
        self.location_map: dict[str, dict] = {}
        self._prepare_locations()
        
        # Words that should NOT be treated as locations
        self.non_location_words = {
            "تاني", "كمان", "زيادة", "المزيد", "باقي", "بقية", 
            "كمل", "continue", "more", "next", "show",
            "اوضه", "اوضة", "غرفه", "غرفة", "room", "bedroom",
            "شقه", "شقة", "شقق", "apartment", "flat",
            "جيب", "عندك", "عندكو", "عندكم", "عندنا",
        }

    def _prepare_locations(self):
        for gov in self.locations:
            gov_en_orig = gov.get("NameInEnglish", "")
            gov_en = TextNormalizer.normalize(gov_en_orig)
            gov_ar = TextNormalizer.normalize(gov.get("NameInArabic", ""))

            entry = {"type": "governorate", "en": gov_en_orig}

            for key in (gov_en, gov_ar):
                if key:
                    self.all_locations.append(key)
                    self.location_map[key] = entry

            for city in gov.get("CitiesAndVillages", []):
                city_en_orig = city.get("NameInEnglish", "")
                city_en = TextNormalizer.normalize(city_en_orig)
                city_ar = TextNormalizer.normalize(city.get("NameInArabic", ""))

                city_entry = {"type": "city", "en": city_en_orig}

                for key in (city_en, city_ar):
                    if key:
                        self.all_locations.append(key)
                        self.location_map[key] = city_entry

    def _phonetic_normalize(self, text: str) -> str:
        """
        Phonetic normalization للعربي
        بيحول أحرف متشابهة صوتياً لحرف واحد
        """
        text = TextNormalizer.normalize(text)

        # أحرف متشابهة صوتياً
        replacements = {
            "ث": "س", "ذ": "ز", "ظ": "ض", "ط": "ت",
            "ة": "ه", "ى": "ي", "ؤ": "و", "ئ": "ي",
            "أ": "ا", "إ": "ا", "آ": "ا",
            "ق": "ك",  # بعض اللهجات
            "ج": "غ",  # في بعض اللهجات
            "ش": "ش",  # نسيبها
            "خ": "ح",  # قريبة
            "ع": "ا",  # في بداية الكلمة
            "غ": "ع",  # متشابهة
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return text

    def detect_location(self, text: str) -> dict | None:
        debug_log("LOCATION_DETECT", f"Detecting location in: {text[:60]}...")
        norm = TextNormalizer.normalize(text)
        if not norm:
            debug_log("LOCATION_DETECT", "Normalized text is empty")
            return None

        # Skip if text only contains non-location words
        words = norm.split()
        if all(word in self.non_location_words for word in words if word):
            debug_log("LOCATION_SKIP", "Text only contains non-location words")
            return None

        sorted_locations = sorted(self.all_locations, key=len, reverse=True)

        # 1. Exact named-location matches are the safest signal.
        for loc in sorted_locations:
            if loc in norm:
                debug_log("LOC_EXACT", loc)
                return self.location_map[loc]

        candidates = self._candidate_phrases(words)

        # 2. Phonetic exact matches keep typo-tolerance without partial false positives
        # like "اوضة" -> "الروضة" or "واي" -> "الوايلي".
        phonetic_locations = {
            self._phonetic_normalize(loc): loc
            for loc in self.all_locations
        }
        for candidate in candidates:
            phonetic_candidate = self._phonetic_normalize(candidate)
            original = phonetic_locations.get(phonetic_candidate)
            if original:
                debug_log("LOC_PHONETIC_EXACT", original)
                return self.location_map[original]

        # 3. Fuzzy matching with higher threshold to reduce false positives
        for candidate in candidates:
            if len(candidate.replace(" ", "")) < 3:
                continue
            candidate_variants = {
                candidate,
                re.sub(r"(.)\1+", r"\1", candidate),
            }
            for variant in candidate_variants:
                matches = difflib.get_close_matches(
                    variant,
                    self.all_locations,
                    n=1,
                    cutoff=0.85,  # Increased to reduce false positives
                )
                if matches:
                    debug_log("LOC_FUZZY", matches[0])
                    return self.location_map[matches[0]]

        # 4. Try word-by-word matching for multi-word locations
        for word in words:
            if len(word) < 3:
                continue
            matches = difflib.get_close_matches(
                word,
                self.all_locations,
                n=1,
                cutoff=0.85,  # Increased to reduce false positives
            )
            if matches:
                debug_log("LOC_WORD_FUZZY", matches[0])
                return self.location_map[matches[0]]

        return None

    def find_in_text(self, text: str) -> dict | None:
        return self.detect_location(text)

    def _candidate_phrases(self, words: list[str]) -> list[str]:
        phrases: list[str] = []
        max_size = min(3, len(words))
        for size in range(max_size, 0, -1):
            for start in range(0, len(words) - size + 1):
                phrase = " ".join(words[start:start + size])
                if phrase not in phrases:
                    phrases.append(phrase)
        return phrases
