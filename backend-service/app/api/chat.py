from fastapi import APIRouter

from app.schemas.chat import ChatRequest, ChatResponse
from app.repositories.memory_repository import MemoryRepository

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)

repository = MemoryRepository()


@router.post(
    "",
    response_model=ChatResponse
)
def chat(request: ChatRequest):

    answer = repository.ask(request.question)

    return ChatResponse(
        answer=answer,
        source="memory"
    )