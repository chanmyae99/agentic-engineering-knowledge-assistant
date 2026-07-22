from __future__ import annotations

from typing import Any

import httpx

from app.web_search.models import (
    WebSearchResponse,
    WebSearchResult,
)


class SerperClient:
    """Asynchronous client for Serper Google Search API."""

    SEARCH_URL = "https://google.serper.dev/search"

    def __init__(
        self,
        api_key: str,
        timeout_seconds: float = 15.0,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("A Serper API key is required.")

        self._api_key = api_key.strip()
        self._client = httpx.AsyncClient(
            timeout=timeout_seconds,
        )

    async def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> WebSearchResponse:
        """Search the web and return normalized organic results."""

        if not isinstance(query, str) or not query.strip():
            raise ValueError("Search query must not be empty.")

        if top_k < 1:
            raise ValueError("top_k must be at least 1.")

        response = await self._client.post(
            self.SEARCH_URL,
            headers={
                "X-API-KEY": self._api_key,
                "Content-Type": "application/json",
            },
            json={
                "q": query.strip(),
                "num": top_k,
            },
        )

        response.raise_for_status()

        payload: dict[str, Any] = response.json()
        organic_results = payload.get("organic", [])

        results = [
            WebSearchResult(
                title=str(item.get("title", "")).strip(),
                link=str(item.get("link", "")).strip(),
                snippet=str(item.get("snippet", "")).strip(),
                position=item.get("position"),
            )
            for item in organic_results[:top_k]
            if item.get("title") and item.get("link")
        ]

        return WebSearchResponse(
            query=query.strip(),
            results=results,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""

        await self._client.aclose()