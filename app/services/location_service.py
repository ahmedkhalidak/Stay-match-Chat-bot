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
        norm = TextNormalizer.normalize(text)
        words = norm.split()

        # ── 0. Phonetic match (أقوى طريقة للأخطاء الإملائية) ──
        phonetic_text = self._phonetic_normalize(text)
        phonetic_locations = {self._phonetic_normalize(loc): loc for loc in self.all_locations}

        if phonetic_text in phonetic_locations:
            original = phonetic_locations[phonetic_text]
            debug_log("LOC_PHONETIC_EXACT", original)
            return self.location_map[original]

        # Check each word phonetically
        for word in words:
            if len(word) < 3:
                continue
            p_word = self._phonetic_normalize(word)
            for p_loc, original in phonetic_locations.items():
                if p_word == p_loc or p_word in p_loc or p_loc in p_word:
                    debug_log("LOC_PHONETIC_PARTIAL", original)
                    return self.location_map[original]

        # ── 1. Exact substring match (longest first) ──
        sorted_locations = sorted(self.all_locations, key=len, reverse=True)
        for loc in sorted_locations:
            if loc in norm:
                debug_log("LOC_EXACT", loc)
                return self.location_map[loc]

        # ── 2. Word boundary match ──
        for word in words:
            if len(word) < 3:
                continue
            for loc in sorted_locations:
                if len(loc) >= 3 and (word in loc or loc in word):
                    debug_log("LOC_PARTIAL", loc)
                    return self.location_map[loc]

        # ── 3. Fuzzy match (cutoff أعلى) ──
        for word in words:
            if len(word) < 3:
                continue
            matches = difflib.get_close_matches(
                word, self.all_locations, n=1, cutoff=0.75
            )
            if matches:
                debug_log("LOC_FUZZY", matches[0])
                return self.location_map[matches[0]]

        # ── 4. Multi-word fuzzy ──
        for i in range(len(words)):
            for j in range(i+1, min(i+3, len(words)+1)):
                phrase = "".join(words[i:j])
                if len(phrase) < 4:
                    continue
                matches = difflib.get_close_matches(
                    phrase, self.all_locations, n=1, cutoff=0.75
                )
                if matches:
                    debug_log("LOC_PHRASE", matches[0])
                    return self.location_map[matches[0]]

        return None

    def find_in_text(self, text: str) -> dict | None:
        return self.detect_location(text)
