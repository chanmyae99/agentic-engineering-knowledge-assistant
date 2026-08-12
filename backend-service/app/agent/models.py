from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentSource(BaseModel):
    """One source supporting the generated answer."""

    source_type: Literal["internal", "web"]

    title: str

    location: str | None = None

    url: str | None = None

    score: float | None = None


class AgentImage(BaseModel):
    """One image retrieved from the internal knowledge base."""

    image_id: str

    document_name: str

    page: int | None = None

    caption: str

    score: float

    image_container: str

    image_blob_name: str

    image_file_name: str

    image_url: str | None = None


class AgentResponse(BaseModel):
    """Final response returned by the agent."""

    answer: str

    route: Literal[
        "internal",
        "web",
        "unavailable",
    ]

    sources: list[AgentSource] = Field(
        default_factory=list,
    )

    images: list[AgentImage] = Field(
        default_factory=list,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )