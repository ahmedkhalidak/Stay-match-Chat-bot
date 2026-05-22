
"""
ChromaDB vector store للـ FAQ.
بيتبني مرة واحدة عند أول استخدام (lazy init).
"""
 
import chromadb
from chromadb.utils import embedding_functions
from app.rag.faq_loader import load_faq_documents
from app.utils.logger import debug_log
 
 
# Sentence-Transformers multilingual model — بيدعم العربي مجاناً
EMBED_MODEL = "intfloat/multilingual-e5-small"
 
_client = None
_collection = None
 
 
def _get_collection():
    global _client, _collection
 
    if _collection is not None:
        return _collection
 
    debug_log("RAG", "Initializing ChromaDB...")
 
    _client = chromadb.Client()  # in-memory (غيّر لـ PersistentClient لو عايز تحفظ)
 
    try:
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBED_MODEL
        )
        debug_log("RAG", f"Using SentenceTransformerEmbeddingFunction with model: {EMBED_MODEL}")
    except Exception as e:
        debug_log("RAG_ERROR", f"Failed to create embedding function: {str(e)}")
        ef = embedding_functions.DefaultEmbeddingFunction()
        debug_log("RAG", "Falling back to DefaultEmbeddingFunction")
 
    _collection = _client.get_or_create_collection(
        name="staymatch_faq",
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )
 
    # لو الـ collection فاضية → لود الـ documents
    if _collection.count() == 0:
        _index_documents()
 
    debug_log("RAG", f"Collection ready — {_collection.count()} docs")
    return _collection
 
 
def _index_documents():
    docs = load_faq_documents()
    collection = _collection
 
    collection.add(
        ids=[d["id"] for d in docs],
        documents=[d["text"] for d in docs],
        metadatas=[
            {
                "answer": d["answer"],
                "question": d["question"],
                "section": d["section"],
            }
            for d in docs
        ],
    )
    debug_log("RAG", f"Indexed {len(docs)} FAQ documents")
 
 
def query_faq(question: str, n_results: int = 3) -> str | None:
    """
    يبحث عن أقرب إجابة للسؤال في الـ ChromaDB.
    بيرجع الإجابة لو الـ similarity فوق حد معين، وإلا None.
    """
    try:
        debug_log("RAG_QUERY", f"Querying FAQ: {question[:80]}...")
        collection = _get_collection()
 
        results = collection.query(
            query_texts=[question],
            n_results=n_results,
            include=["metadatas", "distances", "documents"],
        )
 
        debug_log("RAG_RESULTS_COUNT", f"Retrieved {len(results['ids'][0]) if results['ids'] else 0} candidates")
 
        if not results["ids"] or not results["ids"][0]:
            return None
 
        # Adaptive threshold based on query length
        query_length = len(question.split())
        adaptive_threshold = 0.6 if query_length > 3 else 0.5

        # Check all results and return the best match
        for i in range(len(results["ids"][0])):
            distance = results["distances"][0][i]
            # Cosine distance: 0 = identical, 2 = opposite
            if distance <= adaptive_threshold:
                answer = results["metadatas"][0][i]["answer"]
                question_matched = results["metadatas"][0][i]["question"]
                debug_log("RAG_MATCH", f"distance={distance:.3f} (threshold={adaptive_threshold}) → Q: {question_matched[:40]}... A: {answer[:60]}...")
                return answer

        debug_log("RAG_NO_MATCH", f"Best distance={results['distances'][0][0]:.3f} (threshold={adaptive_threshold}) — too far")
        return None
 
    except Exception as e:
        debug_log("RAG_ERROR", str(e))
        return None

 