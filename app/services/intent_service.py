import re
import difflib

from app.core.session_context import (
    SessionContext
)

from app.services.location_service import (
    LocationService
)
from app.utils.text_normalizer import (
    TextNormalizer
)

class IntentService:

    SEARCH_KEYWORDS = {

    "room": [

        # Arabic / Egyptian Arabic
        "اوضة",
        "أوضة",
        "اوضه",
        "أوضه",
        "قوضة",
        "قوضه",
        "غرفة",
        "غرفه",
        "حجرة",
        "حجره",
        "سكن",
        "سرير",
        "مكان",
        "استوديو",
        "استديو",
        "سنجل",
        "دبل",
        "مشتركة",
        "مشترك",
        "خاصة",
        "خاص",
        "فردية",
        "شباب",
        "طلبة",
        "طلاب",
        "بنات",
        "ولاد",
        "سكن شباب",
        "سكن طلبة",
        "سكن طلاب",
        "غرفة نوم",
        "اوضة نوم",
        "اوضة مشتركة",
        "غرفة مشتركة",
        "اوضة خاصة",
        "غرفة خاصة",

        # English
        "room",
        "rooms",
        "bedroom",
        "private room",
        "shared room",
        "single room",
        "double room",
        "studio",
        "master room",
        "guest room",
        "roommate",
        "bed space",
        "shared",
        "single",
        "private",
        "furnished room",
        "student housing",
        "youth housing",

        # Advanced / alternative
        "chamber",
        "compartment",
        "unit",
        "space",
        "suite",
        "cabin",
    ],

    "property": [

        # Arabic
        "شقة",
        "شقه",
        "شقق",
        "شقة مفروشة",
        "استوديو",
        "استديو",
        "دوبلكس",
        "فيلا",
        "بيت",
        "منزل",
        "عقار",
        "وحدة",
        "سكن",
        "عمارة",
        "برج",

        # English
        "apartment",
        "apartments",
        "flat",
        "property",
        "studio apartment",
        "duplex",
        "villa",
        "house",
        "home",
        "building",
        "residence",
        "real estate",
        "unit",
    ],

    "follow_up": [

        # Price / sorting
        "ارخص",
        "أرخص",
        "اغلى",
        "أغلى",
        "اعلى",
        "أعلى",
        "اقل",
        "أقل",
        "اكتر",
        "أكتر",
        "تحت",
        "فوق",
        "سعر",
        "ميزانية",
        "budget",
        "cheap",
        "cheapest",
        "expensive",
        "lower",
        "higher",
        "price",
        "max",
        "min",

        # Furniture / utilities
        "مفروشة",
        "مفروش",
        "غير مفروشة",
        "مكيف",
        "تكييف",
        "wifi",
        "wi-fi",
        "واي فاي",
        "انترنت",
        "غاز",
        "كهربا",
        "مياه",
        "مطبخ",
        "حمام",
        "غسالة",
        "ثلاجة",
        "بلكونة",

        # Preferences
        "قريب",
        "بعيد",
        "هادئ",
        "واسعة",
        "واسع",
        "نضيف",
        "نظيفة",
        "luxury",
        "modern",
        "clean",
        "quiet",

        # Rental related
        "ايجار",
        "إيجار",
        "rent",
        "rental",
        "شهري",
        "يومي",
        "سنوي",
        "monthly",
        "daily",
        "yearly",
    ],
}

    def __init__(self):

        self.location_service = (
            LocationService()
        )


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

            TextNormalizer.normalize(
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

        text = TextNormalizer.normalize(
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