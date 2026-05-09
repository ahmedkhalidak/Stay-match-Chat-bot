from app.models.search_models import (
    SearchFilters,
)


class FollowUpExtractor:

    PRICE_LOW_KEYWORDS = [
        "ارخص",
        "اقل",
        "أقل",
        "رخيص",
    ]

    PRICE_HIGH_KEYWORDS = [
        "اغلي",
        "أغلى",
        "اعلي",
        "أعلى",
        "غالي",
    ]

    def extract(
        self,
        message: str,
    ) -> SearchFilters | None:

        text = message.lower().strip()

        # ── Cheapest ────────────────────────────
        for keyword in self.PRICE_LOW_KEYWORDS:

            if keyword in text:

                return SearchFilters(
                    sort_by="price_low"
                )

        # ── Highest ─────────────────────────────
        for keyword in self.PRICE_HIGH_KEYWORDS:

            if keyword in text:

                return SearchFilters(
                    sort_by="price_high"
                )

        return None