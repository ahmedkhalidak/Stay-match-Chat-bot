import json
import unicodedata
import difflib
from pathlib import Path
from app.utils.logger import debug_log


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

    def normalize_text(self, text: str) -> str:
        if not text:
            return ""
        text = text.lower().strip()
        replacements = {
            "أ": "ا", "إ": "ا", "آ": "ا",
            "ة": "ه", "ى": "ي", "ؤ": "و", "ئ": "ي",
            "ء": "", "ـ": "",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        text = unicodedata.normalize("NFKD", text)
        # Remove repeated chars
        import re
        text = re.sub(r"(.)\1+", r"\1", text)
        return text

    def _prepare_locations(self):
        for gov in self.locations:
            gov_en_orig = gov.get("NameInEnglish", "")
            gov_en = self.normalize_text(gov_en_orig)
            gov_ar = self.normalize_text(gov.get("NameInArabic", ""))

            entry = {"type": "governorate", "en": gov_en_orig}

            for key in (gov_en, gov_ar):
                if key:
                    self.all_locations.append(key)
                    self.location_map[key] = entry

            for city in gov.get("CitiesAndVillages", []):
                city_en_orig = city.get("NameInEnglish", "")
                city_en = self.normalize_text(city_en_orig)
                city_ar = self.normalize_text(city.get("NameInArabic", ""))

                city_entry = {"type": "city", "en": city_en_orig}

                for key in (city_en, city_ar):
                    if key:
                        self.all_locations.append(key)
                        self.location_map[key] = city_entry

    def detect_location(self, text: str) -> dict | None:
        norm = self.normalize_text(text)
        words = norm.split()

        # 1. Exact substring match (longest first)
        sorted_locations = sorted(self.all_locations, key=len, reverse=True)
        for loc in sorted_locations:
            if loc in norm:
                debug_log("LOC_EXACT", loc)
                return self.location_map[loc]

        # 2. Word boundary match
        for word in words:
            if len(word) < 2:
                continue
            for loc in sorted_locations:
                if len(loc) >= 3 and (word in loc or loc in word):
                    debug_log("LOC_PARTIAL", loc)
                    return self.location_map[loc]

        # 3. Fuzzy match with lower cutoff for typos
        for word in words:
            if len(word) < 3:
                continue
            matches = difflib.get_close_matches(
                word, self.all_locations, n=1, cutoff=0.6
            )
            if matches:
                debug_log("LOC_FUZZY", matches[0])
                return self.location_map[matches[0]]

        # 4. Multi-word fuzzy (e.g. "مدينه نصر" vs "مدينة نصر")
        for i in range(len(words)):
            for j in range(i+1, min(i+3, len(words)+1)):
                phrase = "".join(words[i:j])
                matches = difflib.get_close_matches(
                    phrase, self.all_locations, n=1, cutoff=0.65
                )
                if matches:
                    debug_log("LOC_PHRASE", matches[0])
                    return self.location_map[matches[0]]

        return None

    def find_in_text(self, text: str) -> dict | None:
        return self.detect_location(text)
