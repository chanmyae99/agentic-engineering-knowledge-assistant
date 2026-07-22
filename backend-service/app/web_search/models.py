from pydantic import BaseModel, Field


class WebSearchResult(BaseModel):
    """One web search result returned by Serper."""

    title: str
    link: str
    snippet: str = ""
    position: int | None = None


class WebSearchResponse(BaseModel):
    """Normalized web search response."""

    query: str
    results: list[WebSearchResult] = Field(
        default_factory=list,
    )