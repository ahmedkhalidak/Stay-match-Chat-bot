from app.models.search_models import SearchFilters
from app.services.location_service import LocationService
from app.extractors.price_extractor import PriceExtractor


location_service = LocationService()
price_extractor = PriceExtractor()


class FilterExtractor:
    """
    Fallback extractor يشتغل لو الـ AI فشل.
    الـ AI (QueryExtractor) هو الأصل — ده reserve.
    """

    def extract(self, message: str) -> SearchFilters:

        filters = SearchFilters()
        msg = message.lower()

        # ── Search type ──────────────────────────
        if any(k in msg for k in ["اوضة", "اوضه", "غرفة", "room"]):
            filters.search_type = "room"
        elif any(k in msg for k in ["شقة", "شقه", "apartment"]):
            filters.search_type = "property"

        # ── Location ─────────────────────────────
        loc = location_service.detect_location(message)
        if loc:
            filters.city = loc.get("city")
            filters.governorate = loc.get("governorate")

        # ── Price ────────────────────────────────
        price_data = price_extractor.extract(message)
        filters.min_price = price_data["min_price"]
        filters.max_price = price_data["max_price"]

        # ── Tenant type ──────────────────────────
        if any(k in msg for k in ["طالب", "طلاب", "student"]):
            filters.tenant_type = "student"
        elif any(k in msg for k in ["موظف", "موظفين", "worker", "عامل"]):
            filters.tenant_type = "worker"

        # ── Amenities ────────────────────────────
        if any(k in msg for k in ["wifi", "واي فاي", "وايفاي"]):
            filters.wifi = True

        if any(k in msg for k in ["مفروش", "مفروشة", "furnished"]):
            filters.furnished = True

        if any(k in msg for k in ["بلكونة", "بلكونه", "balcony"]):
            filters.balcony = True

        if any(k in msg for k in ["حمام خاص", "private bathroom", "انسويت"]):
            filters.private_bathroom = True

        # ── Room type ────────────────────────────
        # BUG FIX: كان متداخل جوه if private_bathroom بالغلط
        if any(k in msg for k in ["shared", "شير", "مشاركة", "roommate", "room mate"]):
            filters.shared_room = True
        elif any(k in msg for k in ["سنجل", "single", "private room", "لوحدي"]):
            filters.shared_room = False

        # ── Sorting ──────────────────────────────
        if any(k in msg for k in ["ارخص", "أرخص", "اقل سعر", "رخيص"]):
            filters.sort_by = "price_low"
        elif any(k in msg for k in ["اغلى", "اغلي", "أغلى", "اعلي"]):
            filters.sort_by = "price_high"

        return filters
