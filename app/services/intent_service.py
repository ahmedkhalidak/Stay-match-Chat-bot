import re
import difflib

from app.core.session_context import (
    SessionContext
)

from app.ranking.services.location_service import (
    LocationService
)


class IntentService:

    SEARCH_KEYWORDS = {

        "room": [
            "اوضة",
            "غرفة",
            "room",
            "shared",
            "single",
            "roommate",
        ],

        "property": [
            "شقة",
            "سكن",
            "apartment",
            "flat",
            "property",
        ],

        "follow_up": [
            "ارخص",
            "اغلي",
            "اعلي",
            "اقل",
            "اكتر",
            "تحت",
            "فوق",
            "wifi",
            "واي فاي",
            "مفروشة",
        ],
    }

    def __init__(self):

        self.location_service = (
            LocationService()
        )

    # ──────────────────────────────────────
    # Normalize Text
    # ──────────────────────────────────────

    def normalize_text(
        self,
        text: str,
    ):

        text = text.lower()

        text = re.sub(
            r"[^\w\s]",
            " ",
            text
        )

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

        text = re.sub(
            r"\s+",
            " ",
            text
        ).strip()

        return text

    # ──────────────────────────────────────
    # Fuzzy Contains
    # ──────────────────────────────────────

    def fuzzy_contains(
        self,
        text: str,
        keywords: list[str],
        cutoff: float = 0.75,
    ):

        words = text.split()

        normalized_keywords = [

            self.normalize_text(
                keyword
            )

            for keyword in keywords
        ]

        # Exact match
        for keyword in normalized_keywords:

            if keyword in text:

                return True

        # Fuzzy match
        for word in words:

            matches = difflib.get_close_matches(
                word,
                normalized_keywords,
                n=1,
                cutoff=cutoff,
            )

            if matches:

                return True

        return False

    # ──────────────────────────────────────
    # Detect Intent
    # ──────────────────────────────────────

    def detect_intent(
        self,
        message: str,
        context: SessionContext,
    ):

        text = self.normalize_text(
            message
        )

        # ── Empty ──────────────────────────
        if not text:

            return "empty"

        # ── Pending slot ───────────────────
        if context.pending_slot:

            return "slot_reply"

        # ── Follow-up ──────────────────────
        if (
            context.last_search
            and self.fuzzy_contains(
                text,
                self.SEARCH_KEYWORDS[
                    "follow_up"
                ]
            )
        ):

            return "follow_up"

        # ── Room search ────────────────────
        if self.fuzzy_contains(
            text,
            self.SEARCH_KEYWORDS[
                "room"
            ]
        ):

            return "room_search"

        # ── Property search ────────────────
        if self.fuzzy_contains(
            text,
            self.SEARCH_KEYWORDS[
                "property"
            ]
        ):

            return "property_search"

        # ── Location-only query ────────────
        detected_location = (
            self.location_service.detect_location(
                text
            )
        )

        if detected_location:

            return "location_search"

        # ── Generic housing ────────────────
        housing_words = (
            self.SEARCH_KEYWORDS[
                "room"
            ]
            +
            self.SEARCH_KEYWORDS[
                "property"
            ]
        )

        if self.fuzzy_contains(
            text,
            housing_words
        ):

            return "housing_search"

        # ── Invalid ────────────────────────
        return "invalid"