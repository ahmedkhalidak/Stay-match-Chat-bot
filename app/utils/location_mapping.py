import json
from pathlib import Path
from app.utils.text_normalizer import TextNormalizer


class LocationMapping:
    """
    Dynamic location mapping loaded from locations.json.
    Supports ALL 27 Egyptian governorates equally.
    """

    _instance = None
    _governorate_to_cities: dict[str, list[str]] = {}
    _city_to_governorate: dict[str, str] = {}
    _governorate_aliases: dict[str, str] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        file_path = (
            Path(__file__).resolve().parent.parent
            / "data"
            / "locations.json"
        )
        with open(file_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)

        for gov in data:
            gov_en = gov.get("NameInEnglish", "").strip()
            gov_ar = gov.get("NameInArabic", "").strip()
            if not gov_en:
                continue

            self._governorate_to_cities[gov_en] = []

            # Store normalized aliases for matching
            self._governorate_aliases[
                TextNormalizer.normalize(gov_en)
            ] = gov_en
            if gov_ar:
                self._governorate_aliases[
                    TextNormalizer.normalize(gov_ar)
                ] = gov_en

            # Also map the governorate name itself as a city (capital city)
            self._city_to_governorate[gov_en.lower()] = gov_en
            if gov_ar:
                self._city_to_governorate[
                    TextNormalizer.normalize(gov_ar)
                ] = gov_en

            for city in gov.get("CitiesAndVillages", []):
                city_en = city.get("NameInEnglish", "").strip()
                city_ar = city.get("NameInArabic", "").strip()
                if city_en:
                    self._governorate_to_cities[gov_en].append(city_en)
                    self._city_to_governorate[city_en.lower()] = gov_en
                if city_ar:
                    self._city_to_governorate[
                        TextNormalizer.normalize(city_ar)
                    ] = gov_en

    def get_cities(self, governorate: str) -> list[str]:
        """Return all cities for a given governorate (English name)."""
        norm = TextNormalizer.normalize(governorate)
        gov_key = self._governorate_aliases.get(norm, governorate)
        return self._governorate_to_cities.get(gov_key, [])

    def get_governorate(self, city: str) -> str | None:
        """Return the governorate for a given city."""
        norm = TextNormalizer.normalize(city)
        return self._city_to_governorate.get(norm)

    def is_governorate(self, name: str) -> bool:
        """Check if a name matches a known governorate."""
        norm = TextNormalizer.normalize(name)
        return norm in self._governorate_aliases

    def all_governorates(self) -> list[str]:
        """Return all governorate English names."""
        return list(self._governorate_to_cities.keys())

    def all_cities(self) -> list[str]:
        """Return all city English names."""
        return list(self._city_to_governorate.keys())


# Global singleton
location_mapping = LocationMapping()
