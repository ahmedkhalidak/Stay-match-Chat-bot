"""
LLM Enhancer — بيتصل بس لو الـ Rule Engine فشل.
بيستخدم model رخيص (8b) عشان ماياكلش الـ rate limit.
"""

import json
import time
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from app.core.config import Settings
from app.models.search_models import SearchFilters
from app.prompts.extraction_prompt import EXTRACTION_PROMPT
from app.utils.logger import debug_log

settings = Settings()

# ── Cheap model for extraction ───────────────────
# 70b ياكل ~2000 tokens per call
# 8b ياكل ~500 tokens per call (4x cheaper)
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.0,
    api_key=settings.groq_api_key,
    max_tokens=400,
)

prompt = ChatPromptTemplate.from_messages([
    ("system", EXTRACTION_PROMPT),
    ("human", "{message}"),
])

structured_llm = llm.with_structured_output(
    SearchFilters,
    method="json_mode",
)

extraction_chain = prompt | structured_llm


class QueryExtractor:
    """
    LLM Enhancer — بيتصل بس لو محتاجين.
    بيحاول 3 مرات لو فيه rate limit.
    """

    def extract(self, message: str, history: str = "") -> SearchFilters:
        for attempt in range(3):
            try:
                full_input = message
                if history:
                    full_input = f"[History]\n{history}\n\n[Message]\n{message}"

                result: SearchFilters = extraction_chain.invoke({"message": full_input})
                debug_log("AI_EXTRACTED", result.model_dump())
                return self._sanitize_prices(result)

            except Exception as e:
                error_str = str(e)
                debug_log(f"AI_ERROR_ATTEMPT_{attempt+1}", error_str[:200])

                if "rate_limit" in error_str.lower() or "429" in error_str:
                    wait = 2 ** attempt  # 2, 4, 8 seconds
                    debug_log("RATE_LIMIT_WAIT", f"Waiting {wait}s...")
                    time.sleep(wait)
                    continue

                # Any other error → return invalid immediately
                break

        return SearchFilters(intent="invalid")

    def _sanitize_prices(self, filters: SearchFilters) -> SearchFilters:
        if filters.min_price is not None and filters.min_price < 0:
            filters.min_price = None
        if filters.max_price is not None and filters.max_price < 0:
            filters.max_price = None
        if filters.min_price and filters.max_price and filters.min_price > filters.max_price:
            filters.min_price, filters.max_price = filters.max_price, filters.min_price
        return filters

    def merge_filters(self, base: SearchFilters, update: SearchFilters) -> SearchFilters:
        merged = base.model_copy(deep=True)
        for field, value in update.model_dump().items():
            if field == "intent":
                if value == "follow_up":
                    continue
                elif value in ("room_search", "property_search"):
                    merged.intent = value
                continue
            if value is not None:
                setattr(merged, field, value)
        return merged
