from openai import AsyncOpenAI


class LLMClient:
    """Client for generating grounded responses."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4.1-mini",
    ) -> None:
        self._client = AsyncOpenAI(
            api_key=api_key,
        )
        self._model = model

    async def generate(
        self,
        prompt: str,
    ) -> str:
        response = await self._client.responses.create(
            model=self._model,
            input=prompt,
        )

        return response.output_text.strip()