from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.search_models import SearchFilters


class QuickReply(BaseModel):
    label: str
    value: str


class SearchResultItem(BaseModel):
    id: int | str
    property_id: Optional[int] = None
    result_type: str
    title: str
    subtitle: Optional[str] = None
    location: str
    price_text: str
    monthly_rent: Optional[int] = None
    deposit: Optional[int] = None
    details: list[str] = Field(default_factory=list)
    amenities: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    recommendation_score: Optional[float] = None


class PaginationMeta(BaseModel):
    page: int = 1
    page_size: int = 5
    has_more: bool = False


class ChatResponse(BaseModel):
    reply: str
    response_type: str = "message"
    pending_slot: Optional[str] = None
    filters: Optional[SearchFilters] = None
    suggestions: list[QuickReply] = Field(default_factory=list)
    results: list[SearchResultItem] = Field(default_factory=list)
    pagination: Optional[PaginationMeta] = None
