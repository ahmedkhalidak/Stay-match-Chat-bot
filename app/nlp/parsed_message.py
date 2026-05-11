"""
ParsedMessage — Intermediate Representation
بيمثل كل حاجة استخرجناها من الرسالة قبل ما نحولها لـ SearchFilters
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class LocationResult(BaseModel):
    type: str = ""       # "city" or "governorate"
    en: str = ""         # English name
    ar: str = ""         # Arabic name (original)
    confidence: float = 1.0


class PriceResult(BaseModel):
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    currency: str = "EGP"
    confidence: float = 1.0


class ParsedMessage(BaseModel):
    """
    كل حاجة فهمناها من الرسالة
    """
    # Raw
    raw_text: str = ""
    normalized_text: str = ""
    tokens: List[str] = Field(default_factory=list)

    # Intent
    intent: str = "invalid"          # room_search, property_search, follow_up...
    intent_confidence: float = 0.0

    # Location
    location: Optional[LocationResult] = None
    location_confidence: float = 0.0

    # Price
    price: Optional[PriceResult] = None
    price_confidence: float = 0.0

    # Amenities & Filters
    amenities: Dict[str, Any] = Field(default_factory=dict)
    # e.g. {"wifi": true, "furnished": true, "balcony": false}

    # Tenant & Gender
    tenant_type: Optional[str] = None    # "student" | "worker"
    gender: Optional[str] = None         # "male" | "female"
    shared_room: Optional[bool] = None   # true (shared) | false (single)

    # Sorting
    sort_by: Optional[str] = None        # "price_low" | "price_high"

    # Search Type
    search_type: Optional[str] = None    # "room" | "property"

    # Overall confidence
    overall_confidence: float = 0.0

    # Why LLM was called (for debugging)
    llm_reason: str = ""

    # Raw entities for debugging
    raw_entities: Dict[str, Any] = Field(default_factory=dict)

    def to_search_filters(self) -> "SearchFilters":
        """يحول ParsedMessage → SearchFilters"""
        from app.models.search_models import SearchFilters

        filters = SearchFilters()
        filters.intent = self.intent
        filters.search_type = self.search_type
        filters.tenant_type = self.tenant_type
        filters.gender = self.gender
        filters.shared_room = self.shared_room
        filters.sort_by = self.sort_by

        if self.location:
            if self.location.type == "city":
                filters.city = self.location.en
            else:
                filters.governorate = self.location.en

        if self.price:
            filters.min_price = self.price.min_price
            filters.max_price = self.price.max_price

        # Amenities mapping
        amenity_map = {
            "wifi": "wifi",
            "furnished": "furnished",
            "balcony": "balcony",
            "مكيف": "air_conditioning",
            "air_conditioning": "air_conditioning",
            "حمام_خاص": "private_bathroom",
            "private_bathroom": "private_bathroom",
        }
        for key, field in amenity_map.items():
            if key in self.amenities:
                setattr(filters, field, self.amenities[key])

        return filters

    def calculate_overall_confidence(self) -> float:
        """بيحسب الثقة الإجمالية"""
        scores = [
            self.intent_confidence * 0.35,
            self.location_confidence * 0.25,
            self.price_confidence * 0.15,
        ]

        # Amenities confidence
        if self.amenities:
            scores.append(0.15)

        # Search type confidence
        if self.search_type:
            scores.append(0.10)

        self.overall_confidence = min(sum(scores), 1.0)
        return self.overall_confidence
