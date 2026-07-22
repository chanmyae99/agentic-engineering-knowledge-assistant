from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


@dataclass
class TextUnit:
    """Structured text extracted from one document location."""

    text: str
    page_number: int | None = None
    section: str | None = None
    paragraph_number: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedImage:
    """Image extracted from a PDF or DOCX document."""

    image_index: int
    file_name: str
    mime_type: str
    image_bytes: bytes

    page_number: int | None = None
    paragraph_number: int | None = None

    width: int | None = None
    height: int | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.image_index < 0:
            raise ValueError(
                "image_index must be non-negative."
            )

        if not self.file_name.strip():
            raise ValueError(
                "file_name must not be empty."
            )

        if not self.mime_type.strip():
            raise ValueError(
                "mime_type must not be empty."
            )

        if not self.image_bytes:
            raise ValueError(
                "image_bytes must not be empty."
            )

        if self.page_number is not None and self.page_number < 1:
            raise ValueError(
                "page_number must be at least 1."
            )

        if (
            self.paragraph_number is not None
            and self.paragraph_number < 0
        ):
            raise ValueError(
                "paragraph_number must be non-negative."
            )

        if self.width is not None and self.width < 1:
            raise ValueError(
                "width must be greater than zero."
            )

        if self.height is not None and self.height < 1:
            raise ValueError(
                "height must be greater than zero."
            )


@dataclass
class CaptionedImage:
    """Extracted image together with its generated description."""

    image: ExtractedImage
    caption: str
    caption_model: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.caption.strip():
            raise ValueError(
                "caption must not be empty."
            )

        if not self.caption_model.strip():
            raise ValueError(
                "caption_model must not be empty."
            )


@dataclass
class ParsedDocument:
    """Result returned by a document parser."""

    file_name: str
    file_type: str
    text_units: list[TextUnit]

    images: list[ExtractedImage] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.file_name.strip():
            raise ValueError(
                "file_name must not be empty."
            )

        if not self.file_type.strip():
            raise ValueError(
                "file_type must not be empty."
            )


class IngestionResult(BaseModel):
    """Result of parsing and captioning a document."""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    parsed_document: ParsedDocument
    captioned_images: list[CaptionedImage] = Field(
        default_factory=list
    )