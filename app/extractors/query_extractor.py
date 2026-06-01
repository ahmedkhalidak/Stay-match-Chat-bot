"""
LLM Enhancer — lazy-init, only called when the rule engine fails.
"""

import json
import time
from typing import Optional
from app.models.search_models import SearchFilters
from app.utils.logger import debug_log


class QueryExtractor:
    """LLM fallback — lazily initialized on first use."""

    _chain = None
    _settings = None

    @classmethod
    def _get_chain(cls):
        if cls._chain is not None:
            return cls._chain
        try:
            from langchain_groq import ChatGroq
            from langchain_core.prompts import ChatPromptTemplate
            from app.core.config import Settings
            from app.prompts.extraction_prompt import EXTRACTION_PROMPT

            cls._settings = Settings()
            llm = ChatGroq(
                model="llama-3.1-8b-instant",
                temperature=0.0,
                api_key=cls._settings.groq_api_key,
                max_tokens=400,
            )
            prompt = ChatPromptTemplate.from_messages([
                ("system", EXTRACTION_PROMPT),
                ("human", "{message}"),
            ])
            structured_llm = llm.with_structured_output(SearchFilters, method="json_mode")
            cls._chain = prompt | structured_llm
            debug_log("AI_INIT", "LLM chain initialized (lazy)")
        except Exception as e:
            debug_log("AI_INIT_ERROR", f"LLM init failed: {e}")
            cls._chain = None
        return cls._chain

    def extract(self, message: str, history: str = "") -> SearchFilters:
        chain = self._get_chain()
        if not chain:
            return SearchFilters(intent="invalid")

        for attempt in range(3):
            try:
                full_input = message
                if history:
                    full_input = f"[History]\n{history}\n\n[Message]\n{message}"

                result: SearchFilters = chain.invoke({"message": full_input})
                debug_log("AI_EXTRACTED", result.model_dump())
                return self._sanitize_prices(result)

            except Exception as e:
                error_str = str(e)
                debug_log(f"AI_ERROR_ATTEMPT_{attempt+1}", error_str[:200])

                if "rate_limit" in error_str.lower() or "429" in error_str:
                    wait = 2 ** attempt
                    debug_log("RATE_LIMIT_WAIT", f"Waiting {wait}s...")
                    time.sleep(wait)
                    continue
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