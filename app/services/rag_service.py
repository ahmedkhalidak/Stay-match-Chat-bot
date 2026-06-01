from app.rag.vector_store import query_faq
from app.services.knowledge_service import KnowledgeService
from app.utils.logger import debug_log

_knowledge_service = KnowledgeService()


class RagService:

    def answer(self, message: str, lang: str = "ar") -> str | None:
        debug_log("RAG_INPUT", f"Query: {message} lang={lang}")

        rag_answer = query_faq(message, n_results=3, lang=lang)
        if rag_answer:
            debug_log("RAG_SERVICE", "Answered via ChromaDB")
            return rag_answer

        fuzzy_answer = _knowledge_service.find_answer(message)
        if fuzzy_answer:
            debug_log("RAG_SERVICE", "Answered via KnowledgeService")
            return fuzzy_answer

        debug_log("RAG_NO_ANSWER", "No answer found")
        return None