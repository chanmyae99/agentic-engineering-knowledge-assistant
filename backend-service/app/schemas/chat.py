from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request body for the chat endpoint."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Question for the engineering knowledge assistant.",
        examples=[
            "What PPE should employees wear?",
        ],
    )