from pydantic import BaseModel

from app.models.search_models import (
    SearchFilters,
)


class SessionContext(BaseModel):

    last_search: SearchFilters | None = None

    pending_slot: str | None = None