from app.prompts.agent_prompts import (
    WEB_SEARCH_SYSTEM_PROMPT,
    WEB_SEARCH_USER_TEMPLATE,
)
from app.web_search.models import WebSearchResult


class AgentPromptBuilder:
    """Build prompts using web search results."""

    @staticmethod
    def build(
        question: str,
        results: list[WebSearchResult],
    ) -> str:
        context = []

        for index, result in enumerate(results, start=1):
            context.append(
                "\n".join(
                    [
                        f"Source {index}",
                        f"Title: {result.title}",
                        f"URL: {result.link}",
                        f"Snippet: {result.snippet}",
                    ]
                )
            )

        return (
            WEB_SEARCH_SYSTEM_PROMPT
            + "\n\n"
            + WEB_SEARCH_USER_TEMPLATE.format(
                context="\n\n".join(context),
                question=question,
            )
        )