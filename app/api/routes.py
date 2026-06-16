from fastapi import APIRouter
from sqlalchemy import text
from app.models.chat_models import ChatRequest
from app.models.response_models import ChatResponse
from app.services.search_service import SearchService
from app.database.connection import engine as property_engine
from app.database.chatbot_connection import get_chatbot_engine

router = APIRouter()
search_service = SearchService()


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest):
    return await search_service.handle_message(
        session_id=payload.user_id,
        user_id=payload.user_id,
        message=payload.message,
    )


@router.get("/debug/db-status")
async def debug_db_status():
    """Debug endpoint to check database connection status"""
    property_db_status = "connected"
    chatbot_db_status = "connected"
    property_engine_type = "mssql"
    chatbot_engine_type = "postgresql"
    
    # Test property database connection
    try:
        with property_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        property_db_status = f"error: {str(e)}"
    
    # Test chatbot database connection
    try:
        chatbot_engine = get_chatbot_engine()
        with chatbot_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        chatbot_db_status = f"error: {str(e)}"
    
    return {
        "property_db": property_db_status,
        "chatbot_db": chatbot_db_status,
        "property_engine": property_engine_type,
        "chatbot_engine": chatbot_engine_type
    }
