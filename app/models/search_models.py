from pydantic import BaseModel
from typing import Optional


class SearchFilters(BaseModel):

    intent: Optional[str] = None

    search_type: Optional[str] = None

    city: Optional[str] = None
    governorate: Optional[str] = None

    min_price: Optional[int] = None
    max_price: Optional[int] = None

    tenant_type: Optional[str] = None

    furnished: Optional[bool] = None
    wifi: Optional[bool] = None

    private_bathroom: Optional[bool] = None
    balcony: Optional[bool] = None

    gender: Optional[str] = None

    shared_room: Optional[bool] = None

    sort_by: Optional[str] = None