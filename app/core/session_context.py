from pydantic import BaseModel, Field
from typing import Optional, List
from app.models.search_models import SearchFilters


class MessageTurn(BaseModel):
    role: str
    content: str


class SearchResult(BaseModel):
    filters: SearchFilters
    results_count: int
    timestamp: str = ""


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

    def add_message(self, role: str, content: str):
        self.conversation_history.append(MessageTurn(role=role, content=content))
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]

    def get_history_text(self) -> str:
        if not self.conversation_history:
            return ""
        lines = []
        for turn in self.conversation_history[-6:]:
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

    def go_back(self) -> SearchFilters | None:
        if self.history_index > 0:
            self.history_index -= 1
            return self.search_history[self.history_index].filters
        return None

    def reset_pagination(self):
        self.current_offset = 0
        self.cached_results = []
        self.cache_key = ""
