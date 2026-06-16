import threading
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

# Completely disable ChromaDB telemetry (suppresses noisy telemetry errors in chromadb 1.5.x)
import chromadb.telemetry.product as _tp
_tp.ProductTelemetryClient.capture = lambda self, event: None
from app.rag.faq_loader import load_faq_documents
from app.utils.logger import debug_log

EMBED_MODEL = "intfloat/multilingual-e5-small"

_client = None
_collection = None
_initialized = threading.Event()


def _get_collection():
    global _client, _collection

    if _collection is not None:
        return _collection

    debug_log("RAG", "Initializing ChromaDB...")

    try:
        _client = chromadb.PersistentClient(
            path="/tmp/chromadb_staymatch",
            settings=Settings(anonymized_telemetry=False),
        )
        debug_log("RAG", "Using PersistentClient")
    except Exception:
        _client = chromadb.Client(
            settings=Settings(anonymized_telemetry=False),
        )
        debug_log("RAG", "Falling back to in-memory Client")

    try:
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBED_MODEL
        )
        debug_log("RAG", f"Using model: {EMBED_MODEL}")
    except Exception as e:
        debug_log("RAG_ERROR", f"Embedding model failed: {e}")
        ef = embedding_functions.DefaultEmbeddingFunction()
        debug_log("RAG", "Using DefaultEmbeddingFunction")

    _collection = _client.get_or_create_collection(
        name="staymatch_faq",
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    if _collection.count() == 0:
        _index_documents()

    _initialized.set()
    debug_log("RAG", f"Collection ready — {_collection.count()} docs")
    return _collection


def init_rag(blocking: bool = False):
    """Pre-initialize RAG at startup. If blocking=False, runs in background thread."""
    def _init():
        try:
            _get_collection()
        except Exception as e:
            debug_log("RAG_INIT_ERROR", str(e))

    if blocking:
        _init()
    else:
        t = threading.Thread(target=_init, daemon=True)
        t.start()


def ensure_rag_ready():
    """Block until RAG is initialized (for use during warmup requests)."""
    if not _initialized.is_set():
        _get_collection()


def _index_documents():
    docs = load_faq_documents()
    collection = _collection

    collection.add(
        ids=[d["id"] for d in docs],
        documents=[d["text"] for d in docs],
        metadatas=[
            {
                "answer": d["answer"],
                "answer_en": d.get("answer_en", d["answer"]),
                "question": d["question"],
                "question_en": d.get("question_en", d["question"]),
                "section": d["section"],
            }
            for d in docs
        ],
    )
    debug_log("RAG", f"Indexed {len(docs)} FAQ documents")


def query_faq(question: str, n_results: int = 3, lang: str = "ar") -> str | None:
    try:
        debug_log("RAG_QUERY", f"Query: {question[:80]}...")
        collection = _get_collection()

        results = collection.query(
            query_texts=[question],
            n_results=n_results,
            include=["metadatas", "distances", "documents"],
        )

        if not results["ids"] or not results["ids"][0]:
            return None

        query_length = len(question.split())
        adaptive_threshold = 0.6 if query_length > 3 else 0.5

        for i in range(len(results["ids"][0])):
            distance = results["distances"][0][i]
            if distance <= adaptive_threshold:
                meta = results["metadatas"][0][i]
                answer = meta.get("answer_en" if lang == "en" else "answer", meta["answer"])
                debug_log("RAG_MATCH", f"d={distance:.3f} t={adaptive_threshold} lang={lang}")
                return answer

        debug_log("RAG_NO_MATCH", f"Best d={results['distances'][0][0]:.3f} > {adaptive_threshold}")
        return None

    except Exception as e:
        debug_log("RAG_ERROR", str(e))
        return None


def reset_index():
    """Force re-index on next query (useful for testing)."""
    global _collection, _client
    if _collection is not None:
        try:
            _client.delete_collection("staymatch_faq")
        except Exception:
            pass
    _collection = None