from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Incoming chat request."""

    question: str = Field(
        ...,
        min_length=1,
        description="User question"
    )


class ChatResponse(BaseModel):
    """Outgoing chat response."""

    answer: str
    source: str