from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: background-init RAG (ChromaDB + embedding model)
    try:
        from app.rag.vector_store import init_rag
        init_rag(blocking=False)
    except Exception:
        pass
    yield
    # Shutdown: nothing to clean up


app = FastAPI(
    title="StayMatch AI Service",
    lifespan=lifespan,
)

app.include_router(router)