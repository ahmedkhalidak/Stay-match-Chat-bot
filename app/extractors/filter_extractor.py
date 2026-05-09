from app.models.search_models import SearchFilters

from app.services.location_service import LocationService

from app.extractors.price_extractor import PriceExtractor


location_service = LocationService()

price_extractor = PriceExtractor()


class FilterExtractor:

    def extract(self, message: str) -> SearchFilters:

        filters = SearchFilters()

        msg = message.lower()

        # ── Search type ───────────────────────────
        if any(
            k in msg
            for k in ["اوضة", "اوضه", "غرفة", "room"]
        ):
            filters.search_type = "room"

        elif any(
            k in msg
            for k in ["شقة", "شقه", "apartment"]
        ):
            filters.search_type = "property"

        # ── Location ──────────────────────────────
        loc = location_service.find_in_text(
            message
        )

        if loc:

            if loc["type"] == "city":
                filters.city = loc["en"]

            elif loc["type"] == "governorate":
                filters.governorate = loc["en"]

        # ── Price extraction ──────────────────────
        price_data = price_extractor.extract(
            message
        )

        filters.min_price = price_data[
            "min_price"
        ]

        filters.max_price = price_data[
            "max_price"
        ]

        # ── Tenant type ───────────────────────────
        if any(
            k in msg
            for k in ["طالب", "طلاب", "student"]
        ):
            filters.tenant_type = "student"

        elif any(
            k in msg
            for k in ["موظف", "موظفين", "worker"]
        ):
            filters.tenant_type = "worker"

        # ── Amenities ─────────────────────────────
        if any(
            k in msg
            for k in ["wifi", "واي فاي"]
        ):
            filters.wifi = True

        if any(
            k in msg
            for k in ["مفروش", "مفروشة", "furnished"]
        ):
            filters.furnished = True

        if any(
            k in msg
            for k in ["بلكونة", "بلكونه", "balcony"]
        ):
            filters.balcony = True

        if any(
            k in msg
            for k in ["حمام خاص", "private bathroom"]
        ):
            filters.private_bathroom = True
       # ------------------------------------------------
       # ── Room type ─────────────────────────────
            if any(
               k in msg
               for k in [
                  "shared",
                  "شير",
                  "مشاركة",
                  "roommate",
                  "room mate",
               ]
            ):
               filters.shared_room = True

            elif any(
               k in msg
               for k in [
                  "سنجل",
                  "single",
                  "private room",
                  "لوحدي",
               ]
            ):
               filters.shared_room = False

        # ── Sorting ───────────────────────────────
        if any(
            k in msg
            for k in ["ارخص", "أرخص"]
        ):
            filters.sort_by = "price_low"

        elif any(
            k in msg
            for k in ["اغلى", "اغلي", "أغلى"]
        ):
            filters.sort_by = "price_high"

        # ── Default sorting ───────────────────────
        if filters.sort_by is None:
            filters.sort_by = "relevance"

        return filters