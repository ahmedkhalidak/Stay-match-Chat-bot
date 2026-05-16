from app.models.search_models import (
    SearchFilters,
)
from app.utils.text_normalizer import TextNormalizer


class FollowUpExtractor:

    PRICE_LOW_KEYWORDS = [
        "ارخص",
        "الارخص",
        "اقل",
        "رخيص",
    ]

    PRICE_HIGH_KEYWORDS = [
        "اغلي",
        "اعلي",
        "الاغلي",
        "الاعلي",
        "غالي",
    ]

    def extract(
        self,
        message: str,
    ) -> SearchFilters | None:

        text = TextNormalizer.normalize(message)
        words = set(text.split())

        # ── Cheapest ────────────────────────────
        for keyword in self.PRICE_LOW_KEYWORDS:

            if keyword in words:

                return SearchFilters(
                    sort_by="price_low"
                )

        # ── Highest ─────────────────────────────
        for keyword in self.PRICE_HIGH_KEYWORDS:

            if keyword in words:

                return SearchFilters(
                    sort_by="price_high"
                )

        return None
