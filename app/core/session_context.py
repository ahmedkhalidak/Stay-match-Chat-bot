from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from app.models.search_models import SearchFilters


class MessageTurn(BaseModel):
    role: str
    content: str


class SearchResult(BaseModel):
    filters: SearchFilters
    results_count: int
    timestamp: str = ""


class UserPreferences(BaseModel):
    """Tracked preferences from conversation context"""
    min_budget: Optional[int] = None
    max_budget: Optional[int] = None
    preferred_location: Optional[str] = None  # city or governorate
    tenant_type: Optional[str] = None
    gender: Optional[str] = None
    furnished: Optional[bool] = None
    wifi: Optional[bool] = None
    air_conditioning: Optional[bool] = None
    balcony: Optional[bool] = None
    private_bathroom: Optional[bool] = None
    shared_room: Optional[bool] = None


class SessionContext(BaseModel):
    last_search: Optional[SearchFilters] = None
    pending_slot: Optional[str] = None
    turn_count: int = 0
    conversation_history: List[MessageTurn] = Field(default_factory=list)
    last_results_count: int = 0

    current_offset: int = 0
    page_size: int = 5            # 5 نتائج في الصفحة

    search_history: List[SearchResult] = Field(default_factory=list)
    history_index: int = -1

    cached_results: List[dict] = Field(default_factory=list)
    cache_key: str = ""

    # ── NEW: Smart conversation tracking ──
    user_preferences: UserPreferences = Field(default_factory=UserPreferences)
    seen_property_ids: set[int] = Field(default_factory=set)
    seen_room_ids: set[int] = Field(default_factory=set)
    last_clarification: Optional[str] = None   # "search_type", "location", "price", "amenities"
    no_results_count: int = 0
    total_searches: int = 0

    def add_message(self, role: str, content: str):
        self.conversation_history.append(MessageTurn(role=role, content=content))
        if len(self.conversation_history) > 15:
            self.conversation_history = self.conversation_history[-15:]

    def get_history_text(self) -> str:
        if not self.conversation_history:
            return ""
        lines = []
        for turn in self.conversation_history[-8:]:
            prefix = "User" if turn.role == "user" else "Assistant"
            lines.append(f"{prefix}: {turn.content}")
        return "\n".join(lines)

    def push_search(self, filters: SearchFilters, count: int):
        from datetime import datetime
        self.search_history.append(SearchResult(
            filters=filters,
            results_count=count,
            timestamp=datetime.now().isoformat()
        ))
        if len(self.search_history) > 5:
            self.search_history = self.search_history[-5:]
        self.history_index = len(self.search_history) - 1
        self.total_searches += 1
        if count == 0:
            self.no_results_count += 1
        else:
            self.no_results_count = 0

    def go_back(self) -> SearchFilters | None:
        if self.history_index > 0:
            self.history_index -= 1
            return self.search_history[self.history_index].filters
        return None

    def reset_pagination(self):
        self.current_offset = 0
        self.cached_results = []
        self.cache_key = ""

    def mark_seen(self, property_ids: list[int] = None, room_ids: list[int] = None):
        """Track IDs the user has already seen to avoid duplicates"""
        if property_ids:
            self.seen_property_ids.update(property_ids)
        if room_ids:
            self.seen_room_ids.update(room_ids)

    def update_preferences(self, filters: SearchFilters):
        """Extract and store user preferences from filters"""
        p = self.user_preferences
        if filters.min_price is not None:
            p.min_budget = filters.min_price
        if filters.max_price is not None:
            p.max_budget = filters.max_price
        if filters.city or filters.governorate:
            p.preferred_location = filters.city or filters.governorate
        if filters.tenant_type:
            p.tenant_type = filters.tenant_type
        if filters.gender:
            p.gender = filters.gender
        if filters.furnished is not None:
            p.furnished = filters.furnished
        if filters.wifi is not None:
            p.wifi = filters.wifi
        if filters.air_conditioning is not None:
            p.air_conditioning = filters.air_conditioning
        if filters.balcony is not None:
            p.balcony = filters.balcony
        if filters.private_bathroom is not None:
            p.private_bathroom = filters.private_bathroom
        if filters.shared_room is not None:
            p.shared_room = filters.shared_room

    def get_missing_aspects(self, filters: SearchFilters) -> list[str]:
        """Return what the user hasn't specified yet — for smart questions"""
        missing = []
        if not filters.city and not filters.governorate:
            missing.append("location")
        if filters.min_price is None and filters.max_price is None:
            missing.append("price")
        if filters.furnished is None:
            missing.append("furnished")
        if filters.tenant_type is None:
            missing.append("tenant_type")
        if filters.gender is None:
            missing.append("gender")
        return missing
