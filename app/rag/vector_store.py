import threading
import shutil
import os
from pathlib import Path
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

# Completely disable ChromaDB telemetry (suppresses noisy telemetry errors in chromadb 1.5.x)
import chromadb.telemetry.product as _tp
_tp.ProductTelemetryClient.capture = lambda self, event: None
from app.rag.faq_loader import load_faq_documents
from app.utils.logger import debug_log

EMBED_MODEL = "intfloat/multilingual-e5-small"
CHROMA_PATH = Path("/tmp/chromadb_staymatch")
RAG_EMBEDDINGS_ENABLED = os.getenv("ENABLE_RAG_EMBEDDINGS", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

_client = None
_collection = None
_initialized = threading.Event()


def _create_client(persistent: bool = True):
    if persistent:
        return chromadb.PersistentClient(
            path=str(CHROMA_PATH),
            settings=Settings(anonymized_telemetry=False),
        )
    return chromadb.Client(settings=Settings(anonymized_telemetry=False))


def _get_or_create_collection(client, embedding_function):
    collection = client.get_or_create_collection(
        name="staymatch_faq",
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"},
    )
    # count() forces Chroma to touch its collection schema, which exposes
    # stale persistent-cache mismatches early enough to recover cleanly.
    collection.count()
    return collection


def _get_collection():
    global _client, _collection

    if _collection is not None:
        return _collection

    debug_log("RAG", "Initializing ChromaDB...")

    try:
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBED_MODEL
        )
        debug_log("RAG", f"Using model: {EMBED_MODEL}")
    except Exception as e:
        debug_log("RAG_ERROR", f"Embedding model failed: {e}")
        ef = embedding_functions.DefaultEmbeddingFunction()
        debug_log("RAG", "Using DefaultEmbeddingFunction")

    try:
        _client = _create_client(persistent=True)
        debug_log("RAG", "Using PersistentClient")
        _collection = _get_or_create_collection(_client, ef)
    except Exception as e:
        if "collections.topic" in str(e):
            debug_log("RAG_CACHE_RESET", "Stale Chroma cache detected; rebuilding persistent cache")
            try:
                shutil.rmtree(CHROMA_PATH, ignore_errors=True)
                _client = _create_client(persistent=True)
                _collection = _get_or_create_collection(_client, ef)
            except Exception as rebuild_error:
                debug_log("RAG_FALLBACK", f"Persistent rebuild failed: {rebuild_error}")
                _client = _create_client(persistent=False)
                _collection = _get_or_create_collection(_client, ef)
        else:
            debug_log("RAG_FALLBACK", f"Persistent Chroma failed: {e}")
            _client = _create_client(persistent=False)
            _collection = _get_or_create_collection(_client, ef)

    if _collection.count() == 0:
        _index_documents()

    _initialized.set()
    debug_log("RAG", f"Collection ready — {_collection.count()} docs")
    return _collection


def init_rag(blocking: bool = False):
    """Pre-initialize RAG at startup. If blocking=False, runs in background thread."""
    if not RAG_EMBEDDINGS_ENABLED:
        debug_log("RAG", "Embeddings disabled; using deterministic FAQ fallback only")
        _initialized.set()
        return

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
    if not RAG_EMBEDDINGS_ENABLED:
        _initialized.set()
        return
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
    if not RAG_EMBEDDINGS_ENABLED:
        return None

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
