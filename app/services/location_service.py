import json
import unicodedata
import difflib

from pathlib import Path


class LocationService:

    def __init__(self):

        file_path = (
            Path(__file__)
            .resolve()
            .parent.parent
            / "data"
            / "locations.json"
        )

        with open(
            file_path,
            "r",
            encoding="utf-8-sig"
        ) as file:

            self.locations = json.load(file)

        self.all_locations = []

        self.location_map = {}

        self._prepare_locations()

    # ──────────────────────────────────────
    # Normalize Text
    # ──────────────────────────────────────

    def normalize_text(
        self,
        text: str,
    ):

        if not text:
            return ""

        text = text.lower().strip()

        # Arabic normalization
        replacements = {

            "أ": "ا",
            "إ": "ا",
            "آ": "ا",

            "ة": "ه",

            "ى": "ي",

            "ؤ": "و",
            "ئ": "ي",
        }

        for old, new in (
            replacements.items()
        ):

            text = text.replace(
                old,
                new
            )

        # Unicode normalize
        text = unicodedata.normalize(
            "NFKD",
            text
        )

        return text

    # ──────────────────────────────────────
    # Prepare Locations
    # ──────────────────────────────────────

    def _prepare_locations(self):

        for governorate in self.locations:

            gov_en = self.normalize_text(
                governorate.get(
                    "NameInEnglish",
                    ""
                )
            )

            gov_ar = self.normalize_text(
                governorate.get(
                    "NameInArabic",
                    ""
                )
            )

            original_gov_name = (
                governorate.get(
                    "NameInEnglish",
                    ""
                )
            )

            # Governorate English
            if gov_en:

                self.all_locations.append(
                    gov_en
                )

                self.location_map[
                    gov_en
                ] = {

                    "city": (
                        original_gov_name
                    ),

                    "governorate": (
                        original_gov_name
                    )
                }

            # Governorate Arabic
            if gov_ar:

                self.all_locations.append(
                    gov_ar
                )

                self.location_map[
                    gov_ar
                ] = {

                    "city": (
                        original_gov_name
                    ),

                    "governorate": (
                        original_gov_name
                    )
                }

            # Cities
            for city in governorate.get(
                "CitiesAndVillages",
                []
            ):

                city_en = self.normalize_text(
                    city.get(
                        "NameInEnglish",
                        ""
                    )
                )

                city_ar = self.normalize_text(
                    city.get(
                        "NameInArabic",
                        ""
                    )
                )

                original_city_name = (
                    city.get(
                        "NameInEnglish",
                        ""
                    )
                )

                # City English
                if city_en:

                    self.all_locations.append(
                        city_en
                    )

                    self.location_map[
                        city_en
                    ] = {

                        "city": (
                            original_city_name
                        ),

                        "governorate": (
                            original_gov_name
                        )
                    }

                # City Arabic
                if city_ar:

                    self.all_locations.append(
                        city_ar
                    )

                    self.location_map[
                        city_ar
                    ] = {

                        "city": (
                            original_city_name
                        ),

                        "governorate": (
                            original_gov_name
                        )
                    }

    # ──────────────────────────────────────
    # Detect Location
    # ──────────────────────────────────────

    def detect_location(
        self,
        text: str
    ):

        text = self.normalize_text(
            text
        )

        words = text.split()

        # ── Exact match ─────────────────────
        for location in self.all_locations:

            if location in text:

                return self.location_map[
                    location
                ]

        # ── Partial substring matching ─────
        for word in words:

            for location in self.all_locations:

                if (
                    word in location
                    or location in word
                ):

                    return self.location_map[
                        location
                    ]

        # ── Fuzzy matching ─────────────────
        for word in words:

            matches = difflib.get_close_matches(
                word,
                self.all_locations,
                n=1,
                cutoff=0.75,
            )

            if matches:

                best_match = matches[0]

                return self.location_map[
                    best_match
                ]

        return None