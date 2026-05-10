from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from app.core.config import Settings
from app.models.search_models import SearchFilters
from app.prompts.extraction_prompt import EXTRACTION_PROMPT
from app.utils.logger import debug_log

settings = Settings()

# ── Build the LangChain Chain ──────────────────────
prompt = ChatPromptTemplate.from_messages([
    ("system", EXTRACTION_PROMPT),
    ("human", "{message}"),
])

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.05,
    api_key=settings.groq_api_key,
    max_tokens=500,
)

# Structured output: AI يرجع Pydantic object مباشرة — مفيش JSON parsing يدوي
structured_llm = llm.with_structured_output(
    SearchFilters,
    method="json_mode",
    include_raw=False,
)

extraction_chain = prompt | structured_llm


class QueryExtractor:

    def extract(self, message: str, history: str = "") -> SearchFilters:
        """
        يستخرج الفلاتر باستخدام LangChain + Groq.
        لو فشل، يرجع invalid filter.
        """
        try:
            full_input = message
            if history:
                full_input = (
                    f"[Conversation History]\n{history}\n\n"
                    f"[Current Message]\n{message}"
                )

            result: SearchFilters = extraction_chain.invoke({"message": full_input})
            debug_log("AI_EXTRACTED", result.model_dump())

            # Sanitize prices
            result = self._sanitize_prices(result)
            return result

        except Exception as e:
            debug_log("AI EXTRACTION ERROR", str(e))
            return SearchFilters(intent="invalid")

    def _sanitize_prices(self, filters: SearchFilters) -> SearchFilters:
        """يضمن min < max وكلهم موجبين"""
        if filters.min_price is not None and filters.min_price < 0:
            filters.min_price = None
        if filters.max_price is not None and filters.max_price < 0:
            filters.max_price = None
        if filters.min_price and filters.max_price and filters.min_price > filters.max_price:
            filters.min_price, filters.max_price = filters.max_price, filters.min_price
        return filters

    def merge_filters(self, base: SearchFilters, update: SearchFilters) -> SearchFilters:
        """
        دمج ذكي: القيم الجديدة (غير null) تغلب على القديمة.
        """
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
