"""
Application service for generating embeddings.

This service connects chunking output to the embedding client. It handles:

- converting document chunks into embedding inputs
- splitting large collections into batches
- combining batch responses
- preserving input order and metadata
- generating query embeddings for retrieval
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.chunking.models import DocumentChunk
from app.embedding.exceptions import (
    EmbeddingConfigurationError,
    EmbeddingResponseError,
    EmptyEmbeddingInputError,
)
from app.embedding.models import (
    EmbeddingBatchResult,
    EmbeddingInput,
    EmbeddingVector,
)


class EmbeddingClientProtocol(Protocol):
    """
    Contract required from an embedding client.

    OpenAIEmbeddingClient satisfies this protocol because it provides
    an asynchronous ``embed`` method with the same input and output types.
    """

    async def embed(
        self,
        inputs: Sequence[EmbeddingInput],
    ) -> EmbeddingBatchResult:
        """Generate embeddings for one batch."""


class EmbeddingService:
    """
    Coordinate embedding generation for chunks, queries and generic inputs.

    Parameters
    ----------
    client:
        Embedding provider client, such as ``OpenAIEmbeddingClient``.

    batch_size:
        Maximum number of inputs sent in one provider request.
    """

    def __init__(
        self,
        client: EmbeddingClientProtocol,
        batch_size: int = 32,
    ) -> None:
        if client is None:
            raise EmbeddingConfigurationError(
                "An embedding client is required."
            )

        if batch_size < 1:
            raise EmbeddingConfigurationError(
                "Embedding batch size must be at least 1."
            )

        self.client = client
        self.batch_size = batch_size

    async def embed_chunks(
        self,
        chunks: Sequence[DocumentChunk],
    ) -> EmbeddingBatchResult:
        """
        Generate embeddings for document chunks.

        Chunk content is embedded while source information is retained
        in metadata for later database insertion and retrieval.
        """
        if not chunks:
            raise EmptyEmbeddingInputError(
                "At least one document chunk is required."
            )

        inputs = [
            self._chunk_to_input(chunk)
            for chunk in chunks
        ]

        return await self.embed_inputs(inputs)

    async def embed_inputs(
        self,
        inputs: Sequence[EmbeddingInput],
    ) -> EmbeddingBatchResult:
        """
        Generate embeddings for generic embedding inputs.

        Large collections are divided according to ``batch_size`` and
        returned as one combined result in the original input order.
        """
        if not inputs:
            raise EmptyEmbeddingInputError(
                "At least one embedding input is required."
            )

        self._validate_unique_item_ids(inputs)

        all_embeddings: list[EmbeddingVector] = []
        total_tokens = 0
        tokens_available = True
        response_model: str | None = None

        for start_index in range(0, len(inputs), self.batch_size):
            batch = inputs[
                start_index:start_index + self.batch_size
            ]

            batch_result = await self.client.embed(batch)

            self._validate_batch_result(
                batch=batch,
                result=batch_result,
            )

            if response_model is None:
                response_model = batch_result.model
            elif batch_result.model != response_model:
                raise EmbeddingResponseError(
                    "Embedding provider returned different models "
                    "across batches."
                )

            all_embeddings.extend(batch_result.embeddings)

            if batch_result.total_tokens is None:
                tokens_available = False
            else:
                total_tokens += batch_result.total_tokens

        if response_model is None:
            raise EmbeddingResponseError(
                "No embedding model was returned."
            )

        result = EmbeddingBatchResult(
            embeddings=tuple(all_embeddings),
            model=response_model,
            input_count=len(inputs),
            total_tokens=(
                total_tokens
                if tokens_available
                else None
            ),
        )

        self._validate_complete_result(
            inputs=inputs,
            result=result,
        )

        return result

    async def embed_query(
        self,
        query: str,
    ) -> EmbeddingVector:
        """
        Generate one embedding for a retrieval query.

        The resulting vector can be passed to pgvector similarity search.
        """
        if not isinstance(query, str) or not query.strip():
            raise EmptyEmbeddingInputError(
                "Query text must not be empty."
            )

        query_input = EmbeddingInput(
            item_id="query",
            text=query.strip(),
            metadata={
                "source_type": "query",
            },
        )

        result = await self.embed_inputs([query_input])

        if len(result.embeddings) != 1:
            raise EmbeddingResponseError(
                "Expected exactly one query embedding."
            )

        return result.embeddings[0]

    @staticmethod
    def _chunk_to_input(
        chunk: DocumentChunk,
    ) -> EmbeddingInput:
        """Convert one document chunk into an embedding input."""
        document_id = str(chunk.document_id)
        chunk_index = chunk.chunk_index

        item_id = f"{document_id}:{chunk_index}"

        metadata = {
            "source_type": "chunk",
            "document_id": document_id,
            "chunk_index": chunk_index,
            "content_type": (
                chunk.content_type.value
                if hasattr(chunk.content_type, "value")
                else str(chunk.content_type)
            ),
            "token_count": chunk.token_count,
        }

        section_path = getattr(chunk, "section_path", None)

        if section_path is not None:
            metadata["section_path"] = section_path

        chunk_metadata = getattr(chunk, "metadata", None)

        if chunk_metadata is not None:
            if hasattr(chunk_metadata, "model_dump"):
                metadata["chunk_metadata"] = (
                    chunk_metadata.model_dump(mode="json")
                )
            elif isinstance(chunk_metadata, dict):
                metadata["chunk_metadata"] = dict(chunk_metadata)

        return EmbeddingInput(
            item_id=item_id,
            text=chunk.content,
            metadata=metadata,
        )

    @staticmethod
    def _validate_unique_item_ids(
        inputs: Sequence[EmbeddingInput],
    ) -> None:
        """Ensure all input identifiers are unique."""
        item_ids = [item.item_id for item in inputs]

        if len(item_ids) != len(set(item_ids)):
            raise EmbeddingResponseError(
                "Embedding input item IDs must be unique."
            )

    @staticmethod
    def _validate_batch_result(
        batch: Sequence[EmbeddingInput],
        result: EmbeddingBatchResult,
    ) -> None:
        """Validate one client response before combining it."""
        if result.input_count != len(batch):
            raise EmbeddingResponseError(
                "Embedding batch result count does not match "
                "the submitted batch size."
            )

        expected_ids = [
            item.item_id
            for item in batch
        ]

        actual_ids = [
            embedding.item_id
            for embedding in result.embeddings
        ]

        if actual_ids != expected_ids:
            raise EmbeddingResponseError(
                "Embedding client did not preserve input order. "
                f"Expected {expected_ids}, received {actual_ids}."
            )

    @staticmethod
    def _validate_complete_result(
        inputs: Sequence[EmbeddingInput],
        result: EmbeddingBatchResult,
    ) -> None:
        """Validate the final result assembled from all batches."""
        expected_ids = [
            item.item_id
            for item in inputs
        ]

        actual_ids = [
            embedding.item_id
            for embedding in result.embeddings
        ]

        if actual_ids != expected_ids:
            raise EmbeddingResponseError(
                "Combined embedding result does not match "
                "the original input order."
            )