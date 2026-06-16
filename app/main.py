# Must be set before ANY other import (ChromaDB loads at import time)
import os
os.environ["CHROMA_TELEMETRY"] = "false"
os.environ["CHROMA_SKIP_TELEMETRY"] = "true"

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging
from app.api.routes import router
from app.core.security import security

logger = logging.getLogger("staymatch")


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
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT"
    }
}


# Store original openapi method
_original_openapi = app.openapi


# Override OpenAPI to include custom security scheme
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = _original_openapi()
    openapi_schema["components"]["securitySchemes"] = app.openapi_security_schema
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Middleware to log incoming request headers for diagnostics
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth_present = "Authorization" in request.headers
        logger.info(f"Request: {request.method} {request.url.path} - Authorization present: {auth_present}")
        if auth_present:
            auth_header = request.headers.get("Authorization", "")
            logger.info(f"Authorization header prefix: {auth_header[:20] if auth_header else 'empty'}...")
        response = await call_next(request)
        return response


app.add_middleware(RequestLoggingMiddleware)

app.include_router(router)