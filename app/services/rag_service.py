
"""
RagService — واجهة موحدة للـ RAG في StayMatch.
بيجمع بين:
  1. ChromaDB (semantic search) — الأفضل للأسئلة المتشابهة معنوياً
  2. KnowledgeService (exact/fuzzy) — fallback سريع بدون model
 
الاستخدام في search_service.py:
    from app.services.rag_service import RagService
    rag = RagService()
    answer = rag.answer(message)
    if answer:
        return ChatResponse(reply=answer, response_type="faq")
"""
 
from app.rag.vector_store import query_faq
from app.services.knowledge_service import KnowledgeService
from app.utils.logger import debug_log
 
_knowledge_service = KnowledgeService()
 
 
class RagService:
 
    def answer(self, message: str) -> str | None:
        """
        يحاول يجاوب على السؤال بـ:
        1. ChromaDB semantic search (الأدق)
        2. KnowledgeService fuzzy match (fallback)
        بيرجع None لو مفيش إجابة مناسبة.
        """
        debug_log("RAG_INPUT", f"Query: {message}")
        
        # 1. Semantic RAG
        rag_answer = query_faq(message, n_results=3)
        if rag_answer:
            debug_log("RAG_SERVICE", "Answered via ChromaDB")
            return rag_answer
 
        # 2. Fallback → exact/fuzzy match
        debug_log("RAG_FALLBACK", "Trying KnowledgeService")
        fuzzy_answer = _knowledge_service.find_answer(message)
        if fuzzy_answer:
            debug_log("RAG_SERVICE", "Answered via KnowledgeService fallback")
            return fuzzy_answer
 
        debug_log("RAG_NO_ANSWER", "No answer found")
        return None
