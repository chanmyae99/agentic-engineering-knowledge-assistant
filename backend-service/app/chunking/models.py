"""
Data models used by the structure-aware chunking pipeline.

This module defines the standard representation of document chunks produced
after PDF or DOCX content has been cleaned, analysed, and split.

The models in this file are intentionally independent of:

- Azure Blob Storage
- embedding providers
- PostgreSQL
- retrieval logic

This separation allows the chunking module to be tested independently and
makes the resulting chunks reusable by later pipeline stages.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ContentType(str, Enum):
    """
    Supported content categories for a document chunk.

    Using an enum prevents inconsistent values such as ``"Text"``,
    ``"text_chunk"``, or ``"paragraph"`` from appearing throughout the
    application.

    Attributes:
        TEXT:
            Normal document text made from one or more paragraphs.

        LIST:
            Ordered or unordered list content.

        TABLE:
            Tabular content extracted from a PDF or DOCX document.

        IMAGE_CAPTION:
            Textual description of an extracted image. This type will be used
            in the later image-processing sprint.
    """

    TEXT = "text"
    LIST = "list"
    TABLE = "table"
    IMAGE_CAPTION = "image_caption"


class ChunkMetadata(BaseModel):
    """
    Source information associated with a document chunk.

    This model contains metadata that applies to the source document rather
    than the textual content of the chunk itself.

    Attributes:
        file_name:
            Name of the source file without its Azure virtual folder path.

        blob_name:
            Complete Azure Blob Storage name, including any virtual folder
            prefix.

        file_type:
            Lowercase document extension, such as ``"pdf"`` or ``"docx"``.

        extra:
            Additional metadata that does not yet require a dedicated field.
            This keeps the model extensible without frequently changing its
            schema.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    file_name: str = Field(
        ...,
        min_length=1,
        description="Original source file name.",
        examples=["design-for-safety-guidelines-2026.pdf"],
    )

    blob_name: str = Field(
        ...,
        min_length=1,
        description="Full Azure Blob Storage path of the source document.",
        examples=[
            "guidelines/design-for-safety-guidelines-2026.pdf"
        ],
    )

    file_type: str = Field(
        ...,
        min_length=1,
        description="Lowercase source document type.",
        examples=["pdf"],
    )

    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional additional source metadata.",
    )


class DocumentChunk(BaseModel):
    """
    Represents one validated, structure-aware document chunk.

    A document chunk is the final output of the chunking pipeline. It preserves
    the chunk's content together with its original document structure and
    location.

    The model is designed to support later stages of the application:

    - embedding generation
    - PostgreSQL storage
    - pgvector similarity search
    - keyword retrieval
    - citation generation

    Attributes:
        document_id:
            Application-level identifier for the source document. The value
            will later correspond to the document record in PostgreSQL.

        chunk_index:
            Zero-based sequential position of this chunk within the complete
            document. It must not reset for each page or section.

        content:
            Cleaned textual content of the chunk.

        content_type:
            Category of content stored in the chunk.

        token_count:
            Number of tokens in ``content`` according to the configured
            tokenizer.

        page_start:
            First PDF page represented by this chunk. This remains ``None`` for
            DOCX files when reliable page information is unavailable.

        page_end:
            Last PDF page represented by this chunk.

        section:
            Closest section or heading associated with the chunk.

        section_path:
            Hierarchical path of headings leading to the chunk, for example
            ``["Safety Requirements", "Risk Assessment"]``.

        paragraph_start:
            First source paragraph represented in the chunk.

        paragraph_end:
            Last source paragraph represented in the chunk.

        metadata:
            Source file information and extensible document metadata.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        use_enum_values=True,
    )

    document_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier of the source document.",
    )

    chunk_index: int = Field(
        ...,
        ge=0,
        description="Zero-based sequential index across the entire document.",
    )

    content: str = Field(
        ...,
        min_length=1,
        description="Cleaned textual content of the chunk.",
    )

    content_type: ContentType = Field(
        default=ContentType.TEXT,
        description="Type of content represented by the chunk.",
    )

    token_count: int = Field(
        ...,
        ge=1,
        description="Number of tokens contained in the chunk.",
    )

    page_start: int | None = Field(
        default=None,
        ge=1,
        description="First source PDF page represented by the chunk.",
    )

    page_end: int | None = Field(
        default=None,
        ge=1,
        description="Last source PDF page represented by the chunk.",
    )

    section: str | None = Field(
        default=None,
        description="Closest heading or section associated with the chunk.",
    )

    section_path: list[str] = Field(
        default_factory=list,
        description="Ordered hierarchy of headings for the chunk.",
    )

    paragraph_start: int | None = Field(
        default=None,
        ge=0,
        description="First source paragraph represented by the chunk.",
    )

    paragraph_end: int | None = Field(
        default=None,
        ge=0,
        description="Last source paragraph represented by the chunk.",
    )

    metadata: ChunkMetadata = Field(
        ...,
        description="Source document metadata associated with the chunk.",
    )