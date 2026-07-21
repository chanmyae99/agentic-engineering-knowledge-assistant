"""
Validation utilities for final document chunks.

This module validates ``DocumentChunk`` objects after chunk construction and
before embedding generation or database storage.

The validator does not modify chunks. It only reports errors and warnings.

Phase 1 validates:

- consistent and non-empty document IDs
- sequential and unique chunk indexes
- non-empty chunk content
- valid token counts
- agreement between stored and recalculated token counts
- configured maximum token limits

Later validation rules may include:

- page and paragraph ranges
- section paths
- required metadata
- duplicate chunk content
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

from app.chunking.models import DocumentChunk
from app.chunking.tokenizer import Tokenizer
from app.core.config import get_settings


class ValidationSeverity(str, Enum):
    """
    Severity levels for chunk-validation issues.

    ERROR:
        A problem serious enough to stop ingestion.

    WARNING:
        A quality concern that does not necessarily prevent ingestion.
    """

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """
    Represents one validation problem found in a chunk collection.

    Attributes
    ----------
    severity:
        Whether the issue is an error or warning.

    code:
        Stable machine-readable issue identifier.

    message:
        Human-readable explanation of the problem.

    chunk_index:
        Related chunk index when the issue concerns a specific chunk.

    field_name:
        Related field name when available.
    """

    severity: ValidationSeverity
    code: str
    message: str
    chunk_index: int | None = None
    field_name: str | None = None


@dataclass(slots=True)
class ValidationResult:
    """
    Stores the complete result of a chunk-validation run.

    ``is_valid`` is true when no error-level issues were detected. Warnings do
    not make the result invalid.
    """

    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Return whether validation completed without errors."""
        return not any(
            issue.severity is ValidationSeverity.ERROR
            for issue in self.issues
        )

    @property
    def errors(self) -> list[ValidationIssue]:
        """Return all error-level issues."""
        return [
            issue
            for issue in self.issues
            if issue.severity is ValidationSeverity.ERROR
        ]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """Return all warning-level issues."""
        return [
            issue
            for issue in self.issues
            if issue.severity is ValidationSeverity.WARNING
        ]

    @property
    def error_count(self) -> int:
        """Return the number of validation errors."""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """Return the number of validation warnings."""
        return len(self.warnings)

    def add_error(
        self,
        code: str,
        message: str,
        chunk_index: int | None = None,
        field_name: str | None = None,
    ) -> None:
        """Add one error-level issue."""
        self.issues.append(
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code=code,
                message=message,
                chunk_index=chunk_index,
                field_name=field_name,
            )
        )

    def add_warning(
        self,
        code: str,
        message: str,
        chunk_index: int | None = None,
        field_name: str | None = None,
    ) -> None:
        """Add one warning-level issue."""
        self.issues.append(
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code=code,
                message=message,
                chunk_index=chunk_index,
                field_name=field_name,
            )
        )


class ChunkValidator:
    """
    Validate final chunks before embedding or persistence.

    Parameters
    ----------
    max_tokens:
        Maximum allowed token count for one chunk.

    minimum_warning_tokens:
        Chunks below this value generate a warning. Small chunks may still be
        valid, particularly for short sections or isolated tables.

    tokenizer:
        Optional tokenizer instance. A default ``Tokenizer`` is created when
        one is not supplied.
    """

    def __init__(
        self,
        max_tokens: int | None = None,
        minimum_warning_tokens: int = 20,
        tokenizer: Tokenizer | None = None,
    ) -> None:
        settings = get_settings()

        self.max_tokens = (
            max_tokens
            if max_tokens is not None
            else settings.chunk_max_tokens
        )
        self.minimum_warning_tokens = minimum_warning_tokens
        self.tokenizer = tokenizer or Tokenizer()

        self._validate_configuration()

    def validate(
        self,
        chunks: Iterable[DocumentChunk],
    ) -> ValidationResult:
        """
        Validate an ordered collection of document chunks.

        Parameters
        ----------
        chunks:
            Final chunks generated by ``ChunkBuilder``.

        Returns
        -------
        ValidationResult
            Structured collection of all errors and warnings.

        Notes
        -----
        An empty chunk collection is considered invalid because there would be
        nothing to embed or store.
        """
        chunk_list = list(chunks)
        result = ValidationResult()

        if not chunk_list:
            result.add_error(
                code="EMPTY_CHUNK_COLLECTION",
                message="No chunks were provided for validation.",
            )
            return result

        self._validate_document_ids(chunk_list, result)
        self._validate_chunk_indexes(chunk_list, result)
        self._validate_content(chunk_list, result)
        self._validate_token_counts(chunk_list, result)
        self._validate_page_ranges(chunk_list, result)
        self._validate_paragraph_ranges(chunk_list, result)
        self._validate_required_metadata(chunk_list, result)

        return result

    @staticmethod
    def _validate_document_ids(
        chunks: list[DocumentChunk],
        result: ValidationResult,
    ) -> None:
        """
        Verify that every chunk has the same non-empty document ID.
        """
        normalised_ids: list[str] = []

        for chunk in chunks:
            document_id = str(chunk.document_id).strip()

            if not document_id:
                result.add_error(
                    code="EMPTY_DOCUMENT_ID",
                    message=(
                        f"Chunk {chunk.chunk_index} has an empty document ID."
                    ),
                    chunk_index=chunk.chunk_index,
                    field_name="document_id",
                )
                continue

            normalised_ids.append(document_id)

        unique_ids = set(normalised_ids)

        if len(unique_ids) > 1:
            result.add_error(
                code="INCONSISTENT_DOCUMENT_IDS",
                message=(
                    "All chunks in one validation batch must belong to the "
                    f"same document, but found {len(unique_ids)} document IDs."
                ),
                field_name="document_id",
            )

    @staticmethod
    def _validate_chunk_indexes(
        chunks: list[DocumentChunk],
        result: ValidationResult,
    ) -> None:
        """
        Verify that chunk indexes are unique and sequential from zero.
        """
        indexes = [chunk.chunk_index for chunk in chunks]

        for chunk in chunks:
            if chunk.chunk_index < 0:
                result.add_error(
                    code="NEGATIVE_CHUNK_INDEX",
                    message=(
                        f"Chunk index {chunk.chunk_index} must not be negative."
                    ),
                    chunk_index=chunk.chunk_index,
                    field_name="chunk_index",
                )

        seen_indexes: set[int] = set()
        duplicate_indexes: set[int] = set()

        for index in indexes:
            if index in seen_indexes:
                duplicate_indexes.add(index)

            seen_indexes.add(index)

        for duplicate_index in sorted(duplicate_indexes):
            result.add_error(
                code="DUPLICATE_CHUNK_INDEX",
                message=(
                    f"Chunk index {duplicate_index} appears more than once."
                ),
                chunk_index=duplicate_index,
                field_name="chunk_index",
            )

        expected_indexes = list(range(len(chunks)))

        if indexes != expected_indexes:
            result.add_error(
                code="NON_SEQUENTIAL_CHUNK_INDEXES",
                message=(
                    "Chunk indexes must be ordered sequentially from zero. "
                    f"Expected {expected_indexes}, received {indexes}."
                ),
                field_name="chunk_index",
            )

    @staticmethod
    def _validate_content(
        chunks: list[DocumentChunk],
        result: ValidationResult,
    ) -> None:
        """
        Verify that every chunk contains meaningful non-empty text.
        """
        for chunk in chunks:
            content = chunk.content

            if not content or not content.strip():
                result.add_error(
                    code="EMPTY_CHUNK_CONTENT",
                    message=(
                        f"Chunk {chunk.chunk_index} has empty content."
                    ),
                    chunk_index=chunk.chunk_index,
                    field_name="content",
                )

    def _validate_token_counts(
        self,
        chunks: list[DocumentChunk],
        result: ValidationResult,
    ) -> None:
        """
        Validate stored token counts against content and configured limits.
        """
        for chunk in chunks:
            stored_count = chunk.token_count

            if stored_count < 0:
                result.add_error(
                    code="NEGATIVE_TOKEN_COUNT",
                    message=(
                        f"Chunk {chunk.chunk_index} has a negative token "
                        f"count: {stored_count}."
                    ),
                    chunk_index=chunk.chunk_index,
                    field_name="token_count",
                )
                continue

            calculated_count = self.tokenizer.count_tokens(
                chunk.content
            )

            if stored_count != calculated_count:
                result.add_error(
                    code="TOKEN_COUNT_MISMATCH",
                    message=(
                        f"Chunk {chunk.chunk_index} stores token_count="
                        f"{stored_count}, but recalculation returned "
                        f"{calculated_count}."
                    ),
                    chunk_index=chunk.chunk_index,
                    field_name="token_count",
                )

            if calculated_count > self.max_tokens:
                result.add_error(
                    code="CHUNK_EXCEEDS_MAX_TOKENS",
                    message=(
                        f"Chunk {chunk.chunk_index} contains "
                        f"{calculated_count} tokens, exceeding the maximum "
                        f"of {self.max_tokens}."
                    ),
                    chunk_index=chunk.chunk_index,
                    field_name="token_count",
                )

            if 0 < calculated_count < self.minimum_warning_tokens:
                result.add_warning(
                    code="VERY_SMALL_CHUNK",
                    message=(
                        f"Chunk {chunk.chunk_index} contains only "
                        f"{calculated_count} tokens. Very small chunks may "
                        "reduce retrieval quality."
                    ),
                    chunk_index=chunk.chunk_index,
                    field_name="token_count",
                )

    def _validate_configuration(self) -> None:
        """Validate validator configuration values."""
        if self.max_tokens < 1:
            raise ValueError("max_tokens must be at least 1.")

        if self.minimum_warning_tokens < 0:
            raise ValueError(
                "minimum_warning_tokens must not be negative."
            )

        if self.minimum_warning_tokens > self.max_tokens:
            raise ValueError(
                "minimum_warning_tokens must not exceed max_tokens."
            )
        
    @staticmethod
    def _validate_page_ranges(
        chunks: list[DocumentChunk],
        result: ValidationResult,
    ) -> None:
        """Validate page ranges stored in metadata.extra."""
        for chunk in chunks:
            extra = chunk.metadata.extra or {}

            page_start = extra.get("page_start")
            page_end = extra.get("page_end")

            if (
                page_start is not None
                and page_end is not None
                and page_end < page_start
            ):
                result.add_error(
                    code="INVALID_PAGE_RANGE",
                    message=(
                        f"Chunk {chunk.chunk_index} has page_end "
                        f"({page_end}) before page_start ({page_start})."
                    ),
                    chunk_index=chunk.chunk_index,
                    field_name="page_range",
                )

    @staticmethod
    def _validate_paragraph_ranges(
        chunks: list[DocumentChunk],
        result: ValidationResult,
    ) -> None:
        """Validate paragraph ranges stored in metadata.extra."""
        for chunk in chunks:
            extra = chunk.metadata.extra or {}

            paragraph_start = extra.get("paragraph_start")
            paragraph_end = extra.get("paragraph_end")

            if (
                paragraph_start is not None
                and paragraph_end is not None
                and paragraph_end < paragraph_start
            ):
                result.add_error(
                    code="INVALID_PARAGRAPH_RANGE",
                    message=(
                        f"Chunk {chunk.chunk_index} has paragraph_end "
                        f"({paragraph_end}) before paragraph_start "
                        f"({paragraph_start})."
                    ),
                    chunk_index=chunk.chunk_index,
                    field_name="paragraph_range",
                )
        
    @staticmethod
    def _validate_required_metadata(
        chunks: list[DocumentChunk],
        result: ValidationResult,
    ) -> None:
        """
        Validate that essential metadata exists.
        """
        for chunk in chunks:
            metadata = chunk.metadata

            if not metadata.file_name.strip():
                result.add_error(
                    code="MISSING_FILE_NAME",
                    message=f"Chunk {chunk.chunk_index} has no file name.",
                    chunk_index=chunk.chunk_index,
                    field_name="file_name",
                )

            if not metadata.blob_name.strip():
                result.add_error(
                    code="MISSING_BLOB_NAME",
                    message=f"Chunk {chunk.chunk_index} has no blob name.",
                    chunk_index=chunk.chunk_index,
                    field_name="blob_name",
                )

            if not metadata.file_type.strip():
                result.add_error(
                    code="MISSING_FILE_TYPE",
                    message=f"Chunk {chunk.chunk_index} has no file type.",
                    chunk_index=chunk.chunk_index,
                    field_name="file_type",
                )