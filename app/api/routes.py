from fastapi import APIRouter

from app.models.chat_models import ChatRequest
from app.models.response_models import ChatResponse

from app.services.search_service import SearchService


router = APIRouter()

search_service = SearchService()


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest):

    reply = search_service.handle_message(
        payload.session_id,
        payload.message,
    )

    return ChatResponse(reply=reply)