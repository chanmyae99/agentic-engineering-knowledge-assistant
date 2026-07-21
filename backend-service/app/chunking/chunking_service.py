"""
Orchestration service for structure-aware document chunking.

The service coordinates:

1. Text cleaning
2. Structure analysis
3. Chunk construction
4. Chunk validation

It does not generate embeddings or write data to the database.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable

from app.chunking.chunk_builder import ChunkBuilder
from app.chunking.cleaner import TextCleaner
from app.chunking.models import DocumentChunk
from app.chunking.structure_analyzer import StructureAnalyzer
from app.chunking.validator import (
    ChunkValidator,
    ValidationIssue,
    ValidationResult,
)

logger = logging.getLogger(__name__)


class ChunkingError(RuntimeError):
    """Base exception for chunking pipeline failures."""


class EmptyParsedDocumentError(ChunkingError):
    """Raised when the parser returns no usable document units."""


class ChunkValidationError(ChunkingError):
    """Raised when generated chunks fail validation."""

    def __init__(self, result: ValidationResult) -> None:
        self.result = result

        error_messages = "; ".join(
            f"{issue.code}: {issue.message}"
            for issue in result.errors
        )

        super().__init__(
            "Generated chunks failed validation. "
            f"Errors: {error_messages}"
        )


@dataclass(frozen=True, slots=True)
class ChunkingResult:
    """
    Result returned by the chunking service.

    Attributes
    ----------
    chunks:
        Successfully generated and validated chunks.

    warnings:
        Non-blocking validation warnings.
    """

    chunks: list[DocumentChunk]
    warnings: list[ValidationIssue]

    @property
    def chunk_count(self) -> int:
        """Return the number of generated chunks."""
        return len(self.chunks)

    @property
    def warning_count(self) -> int:
        """Return the number of non-blocking warnings."""
        return len(self.warnings)


class ChunkingService:
    """
    Coordinate the complete structure-aware chunking workflow.

    Parameters
    ----------
    cleaner:
        Text cleaner implementation.

    analyzer:
        Structure analyzer implementation.

    builder:
        Chunk builder implementation.

    validator:
        Final chunk validator implementation.
    """

    def __init__(
        self,
        cleaner: TextCleaner | None = None,
        analyzer: StructureAnalyzer | None = None,
        builder: ChunkBuilder | None = None,
        validator: ChunkValidator | None = None,
    ) -> None:
        self.cleaner = cleaner or TextCleaner()
        self.analyzer = analyzer or StructureAnalyzer()
        self.builder = builder or ChunkBuilder()
        self.validator = validator or ChunkValidator()

    def process(
        self,
        parsed_units: Iterable[dict[str, Any]],
        document_id: str,
        file_name: str,
        blob_name: str,
        file_type: str,
    ) -> ChunkingResult:
        """
        Clean, analyse, build and validate chunks for one document.

        Parameters
        ----------
        parsed_units:
            Paragraphs, headings, lists or tables returned by the parser.
            Each unit must contain a ``text`` field. Other fields such as
            ``style``, ``page_number`` and ``paragraph_number`` are preserved.

        document_id:
            Unique identifier for the source document.

        file_name:
            Original source file name.

        blob_name:
            Full Azure Blob Storage object name.

        file_type:
            Source type such as ``pdf`` or ``docx``.

        Returns
        -------
        ChunkingResult
            Validated chunks and any non-blocking warnings.

        Raises
        ------
        ValueError
            When required document values are blank.

        EmptyParsedDocumentError
            When no usable text remains after cleaning.

        ChunkValidationError
            When one or more generated chunks fail validation.
        """
        self._validate_request(
            document_id=document_id,
            file_name=file_name,
            blob_name=blob_name,
            file_type=file_type,
        )

        units = list(parsed_units)

        if not units:
            raise EmptyParsedDocumentError(
                f"No parsed units were provided for '{file_name}'."
            )

        logger.info(
            "Starting chunking for document_id=%s file_name=%s units=%d",
            document_id,
            file_name,
            len(units),
        )

        cleaned_units = self._clean_units(units)

        if not cleaned_units:
            raise EmptyParsedDocumentError(
                f"No usable text remained after cleaning '{file_name}'."
            )

        structured_elements = self.analyzer.analyze(
            cleaned_units,
            file_type,
        )

        if not structured_elements:
            raise EmptyParsedDocumentError(
                f"No structured elements were produced for '{file_name}'."
            )

        chunks = self.builder.build_chunks(
            structured_elements,
            document_id,
            file_name,
            blob_name,
            file_type,
        )

        validation_result = self.validator.validate(chunks)

        if not validation_result.is_valid:
            logger.error(
                "Chunk validation failed for document_id=%s errors=%d",
                document_id,
                validation_result.error_count,
            )
            raise ChunkValidationError(validation_result)

        for warning in validation_result.warnings:
            logger.warning(
                "Chunk validation warning document_id=%s "
                "chunk_index=%s code=%s message=%s",
                document_id,
                warning.chunk_index,
                warning.code,
                warning.message,
            )

        logger.info(
            "Chunking completed for document_id=%s chunks=%d warnings=%d",
            document_id,
            len(chunks),
            validation_result.warning_count,
        )

        return ChunkingResult(
            chunks=chunks,
            warnings=validation_result.warnings,
        )

    @staticmethod
    def _clean_units(
        parsed_units: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Clean unit text while preserving parser metadata.

        Units whose text becomes empty after cleaning are removed.
        """
        cleaned_units: list[dict[str, Any]] = []

        for unit in parsed_units:
            if not isinstance(unit, dict):
                raise TypeError(
                    "Every parsed document unit must be a dictionary."
                )

            raw_text = unit.get("text", "")

            if raw_text is None:
                raw_text = ""

            cleaned_text = TextCleaner.clean_text(str(raw_text))

            if not cleaned_text.strip():
                continue

            cleaned_unit = dict(unit)
            cleaned_unit["text"] = cleaned_text
            cleaned_units.append(cleaned_unit)

        return cleaned_units

    @staticmethod
    def _validate_request(
        document_id: str,
        file_name: str,
        blob_name: str,
        file_type: str,
    ) -> None:
        """Validate required document-level inputs."""
        required_values = {
            "document_id": document_id,
            "file_name": file_name,
            "blob_name": blob_name,
            "file_type": file_type,
        }

        for field_name, value in required_values.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"{field_name} must be a non-empty string."
                )