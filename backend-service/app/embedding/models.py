"""
Domain models for the embedding pipeline.

These models provide an internal contract between:

- ChunkingService
- EmbeddingClient
- EmbeddingService
- PostgreSQL repositories

They do not contain OpenAI API or database logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence


@dataclass(frozen=True, slots=True)
class EmbeddingInput:
    """
    One text item that requires an embedding.

    Attributes
    ----------
    item_id:
        Identifier of the source item, such as a chunk ID or image ID.

    text:
        Text that will be sent to the embedding provider.

    metadata:
        Optional information carried through the embedding pipeline.
    """

    item_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate the embedding input."""
        if not isinstance(self.item_id, str) or not self.item_id.strip():
            raise ValueError("item_id must be a non-empty string.")

        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("text must be a non-empty string.")

        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dictionary.")


@dataclass(frozen=True, slots=True)
class EmbeddingVector:
    """
    Embedding generated for one source item.

    Attributes
    ----------
    item_id:
        Identifier copied from the corresponding ``EmbeddingInput``.

    vector:
        Numeric embedding values returned by the embedding provider.

    model:
        Embedding model used to generate the vector.

    dimensions:
        Number of values in the vector.

    metadata:
        Metadata copied from the source input.
    """

    item_id: str
    vector: tuple[float, ...]
    model: str
    dimensions: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate the generated embedding."""
        if not isinstance(self.item_id, str) or not self.item_id.strip():
            raise ValueError("item_id must be a non-empty string.")

        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("model must be a non-empty string.")

        if self.dimensions < 1:
            raise ValueError("dimensions must be at least 1.")

        if len(self.vector) != self.dimensions:
            raise ValueError(
                "Vector length does not match dimensions: "
                f"received {len(self.vector)}, expected {self.dimensions}."
            )

        if not self.vector:
            raise ValueError("vector must not be empty.")

        if not all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            for value in self.vector
        ):
            raise TypeError(
                "Every embedding vector value must be numeric."
            )

        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dictionary.")

    @classmethod
    def create(
        cls,
        item_id: str,
        vector: Sequence[float],
        model: str,
        metadata: dict[str, Any] | None = None,
    ) -> "EmbeddingVector":
        """
        Construct an embedding from any numeric sequence.

        The sequence is converted to an immutable tuple so the completed
        result cannot be modified accidentally.
        """
        normalised_vector = tuple(float(value) for value in vector)

        return cls(
            item_id=item_id,
            vector=normalised_vector,
            model=model,
            dimensions=len(normalised_vector),
            metadata=dict(metadata or {}),
        )

    def as_list(self) -> list[float]:
        """
        Return the vector as a list for pgvector or API serialization.
        """
        return list(self.vector)


@dataclass(frozen=True, slots=True)
class EmbeddingBatchResult:
    """
    Result of embedding one complete batch.

    Attributes
    ----------
    embeddings:
        Generated vectors in the same order as their source inputs.

    model:
        Embedding model used for the batch.

    input_count:
        Number of source inputs submitted.

    total_tokens:
        Token usage returned by the provider when available.
    """

    embeddings: tuple[EmbeddingVector, ...]
    model: str
    input_count: int
    total_tokens: int | None = None

    def __post_init__(self) -> None:
        """Validate batch-level consistency."""
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("model must be a non-empty string.")

        if self.input_count < 0:
            raise ValueError("input_count must not be negative.")

        if len(self.embeddings) != self.input_count:
            raise ValueError(
                "Embedding count does not match input_count: "
                f"received {len(self.embeddings)}, "
                f"expected {self.input_count}."
            )

        if self.total_tokens is not None and self.total_tokens < 0:
            raise ValueError("total_tokens must not be negative.")

        for embedding in self.embeddings:
            if embedding.model != self.model:
                raise ValueError(
                    "Every embedding in a batch must use the same model."
                )

    @property
    def dimensions(self) -> int | None:
        """
        Return the common vector dimension.

        Empty batches return ``None``.
        """
        if not self.embeddings:
            return None

        return self.embeddings[0].dimensions

    def vectors_as_lists(self) -> list[list[float]]:
        """
        Return vectors in a repository-friendly format.
        """
        return [
            embedding.as_list()
            for embedding in self.embeddings
        ]

    def get_by_item_id(
        self,
        item_id: str,
    ) -> EmbeddingVector | None:
        """
        Find an embedding using its source item identifier.
        """
        for embedding in self.embeddings:
            if embedding.item_id == item_id:
                return embedding

        return None