"""
Asynchronous OpenAI client for generating text embeddings.

The client is responsible only for communicating with the OpenAI
Embeddings API and converting API responses into application domain models.
"""

from __future__ import annotations

from collections.abc import Sequence

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)

from app.embedding.exceptions import (
    EmbeddingConfigurationError,
    EmbeddingDimensionError,
    EmbeddingGenerationError,
    EmbeddingResponseError,
    EmptyEmbeddingInputError,
)
from app.embedding.models import (
    EmbeddingBatchResult,
    EmbeddingInput,
    EmbeddingVector,
)


class OpenAIEmbeddingClient:
    """
    Generate text embeddings through the OpenAI API.

    Parameters
    ----------
    api_key:
        OpenAI API key.

    model:
        Embedding model name.

    expected_dimensions:
        Required number of dimensions for each returned vector.

    timeout:
        Maximum request duration in seconds.

    max_retries:
        Number of retries performed by the OpenAI SDK.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        expected_dimensions: int = 1536,
        timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        self.api_key = api_key.strip() if api_key else ""
        self.model = model.strip() if model else ""
        self.expected_dimensions = expected_dimensions

        self._validate_configuration(
            timeout=timeout,
            max_retries=max_retries,
        )

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            timeout=timeout,
            max_retries=max_retries,
        )

    async def embed(
        self,
        inputs: Sequence[EmbeddingInput],
    ) -> EmbeddingBatchResult:
        """
        Generate embeddings for one batch of inputs.

        Embeddings are returned in the same logical order as the supplied
        inputs. Response indexes are checked before results are constructed.
        """
        if not inputs:
            raise EmptyEmbeddingInputError(
                "At least one embedding input is required."
            )

        self._validate_inputs(inputs)

        texts = [item.text for item in inputs]

        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts,
                encoding_format="float",
            )

        except RateLimitError as exc:
            raise EmbeddingGenerationError(
                "OpenAI embedding request was rate limited."
            ) from exc

        except APITimeoutError as exc:
            raise EmbeddingGenerationError(
                "OpenAI embedding request timed out."
            ) from exc

        except APIConnectionError as exc:
            raise EmbeddingGenerationError(
                "Unable to connect to the OpenAI API."
            ) from exc

        except APIStatusError as exc:
            raise EmbeddingGenerationError(
                "OpenAI returned an unsuccessful response "
                f"with status code {exc.status_code}."
            ) from exc

        except Exception as exc:
            raise EmbeddingGenerationError(
                "Unexpected failure while generating embeddings."
            ) from exc

        return self._build_result(
            inputs=inputs,
            response=response,
        )

    async def embed_text(
        self,
        item_id: str,
        text: str,
        metadata: dict | None = None,
    ) -> EmbeddingVector:
        """
        Generate one embedding.

        This convenience method still uses the standard batch implementation.
        """
        source = EmbeddingInput(
            item_id=item_id,
            text=text,
            metadata=dict(metadata or {}),
        )

        result = await self.embed([source])

        if not result.embeddings:
            raise EmbeddingResponseError(
                "OpenAI returned no embedding for the supplied text."
            )

        return result.embeddings[0]

    async def close(self) -> None:
        """Close the underlying asynchronous HTTP client."""
        await self.client.close()

    def _build_result(
        self,
        inputs: Sequence[EmbeddingInput],
        response: object,
    ) -> EmbeddingBatchResult:
        """Validate and convert the provider response."""
        response_data = getattr(response, "data", None)

        if response_data is None:
            raise EmbeddingResponseError(
                "OpenAI response does not contain a data field."
            )

        if len(response_data) != len(inputs):
            raise EmbeddingResponseError(
                "OpenAI returned an unexpected number of embeddings: "
                f"received {len(response_data)}, "
                f"expected {len(inputs)}."
            )

        ordered_data = sorted(
            response_data,
            key=lambda item: item.index,
        )

        expected_indexes = list(range(len(inputs)))
        actual_indexes = [item.index for item in ordered_data]

        if actual_indexes != expected_indexes:
            raise EmbeddingResponseError(
                "OpenAI returned invalid embedding indexes: "
                f"{actual_indexes}."
            )

        vectors: list[EmbeddingVector] = []

        for source, provider_item in zip(
            inputs,
            ordered_data,
            strict=True,
        ):
            raw_vector = getattr(
                provider_item,
                "embedding",
                None,
            )

            if not raw_vector:
                raise EmbeddingResponseError(
                    f"OpenAI returned an empty vector for "
                    f"item '{source.item_id}'."
                )

            if len(raw_vector) != self.expected_dimensions:
                raise EmbeddingDimensionError(
                    "Embedding dimension mismatch for "
                    f"item '{source.item_id}': "
                    f"received {len(raw_vector)}, "
                    f"expected {self.expected_dimensions}."
                )

            vectors.append(
                EmbeddingVector.create(
                    item_id=source.item_id,
                    vector=raw_vector,
                    model=self.model,
                    metadata=source.metadata,
                )
            )

        usage = getattr(response, "usage", None)
        total_tokens = (
            getattr(usage, "total_tokens", None)
            if usage is not None
            else None
        )

        return EmbeddingBatchResult(
            embeddings=tuple(vectors),
            model=self.model,
            input_count=len(inputs),
            total_tokens=total_tokens,
        )

    def _validate_configuration(
        self,
        timeout: float,
        max_retries: int,
    ) -> None:
        """Validate client configuration before creating the SDK client."""
        if not self.api_key:
            raise EmbeddingConfigurationError(
                "OpenAI API key is required."
            )

        if not self.model:
            raise EmbeddingConfigurationError(
                "OpenAI embedding model is required."
            )

        if self.expected_dimensions < 1:
            raise EmbeddingConfigurationError(
                "Expected embedding dimensions must be at least 1."
            )

        if timeout <= 0:
            raise EmbeddingConfigurationError(
                "Timeout must be greater than zero."
            )

        if max_retries < 0:
            raise EmbeddingConfigurationError(
                "Maximum retries cannot be negative."
            )

    @staticmethod
    def _validate_inputs(
        inputs: Sequence[EmbeddingInput],
    ) -> None:
        """Check batch identifiers before sending the API request."""
        item_ids = [item.item_id for item in inputs]

        if len(item_ids) != len(set(item_ids)):
            raise EmbeddingResponseError(
                "Embedding input item IDs must be unique within a batch."
            )