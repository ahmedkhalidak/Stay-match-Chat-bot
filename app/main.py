# Must be set before ANY other import (ChromaDB loads at import time)
import os
os.environ["CHROMA_TELEMETRY"] = "false"
os.environ["CHROMA_SKIP_TELEMETRY"] = "true"

from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.routes import router
from app.core.security import security


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
    security=[{"Bearer": []}],
)

app.include_router(router)