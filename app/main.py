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
    security=[{"BearerAuth": []}],
)


# Configure OpenAPI security scheme for Bearer JWT authentication
app.openapi_security_schema = {
    "BearerAuth": {
        "type": "apiKey",
        "in": "header",
        "name": "Authorization",
        "description": "Enter the full Authorization header value including 'Bearer' prefix (e.g., 'Bearer eyJhbGci...')"
    }
}


# Override OpenAPI to include custom security scheme
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = app.openapi()
    openapi_schema["components"]["securitySchemes"] = app.openapi_security_schema
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

app.include_router(router)