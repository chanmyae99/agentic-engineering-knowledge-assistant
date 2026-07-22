from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentSource(BaseModel):
    """One source supporting the generated answer."""

    source_type: Literal["internal", "web"]

    title: str

    location: str | None = None

    url: str | None = None

    score: float | None = None


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

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )