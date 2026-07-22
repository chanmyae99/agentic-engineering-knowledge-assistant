"""
Image extraction utilities for PDF and DOCX documents.

The parsers remain responsible for opening documents. This class handles
only image-specific extraction and conversion into ExtractedImage models.
"""

from __future__ import annotations

import mimetypes
from io import BytesIO
from pathlib import Path
from typing import Any

import fitz
from docx.document import Document as DOCXDocument
from PIL import Image, UnidentifiedImageError

from app.ingestion.exceptions import (
    ImageExtractionError,
    InvalidImageError,
)
from app.ingestion.models import ExtractedImage


class ImageExtractor:
    """Extract embedded images from PDF pages and DOCX documents."""

    def extract_from_pdf_page(
        self,
        document: fitz.Document,
        page: fitz.Page,
        page_number: int,
        starting_index: int = 0,
    ) -> list[ExtractedImage]:
        """
        Extract all embedded images referenced by one PDF page.

        Parameters
        ----------
        document:
            Open PyMuPDF document.

        page:
            Page currently being processed.

        page_number:
            Human-readable page number beginning from 1.

        starting_index:
            Index assigned to the first extracted image from this page.
        """
        if page_number < 1:
            raise ValueError("page_number must be at least 1.")

        if starting_index < 0:
            raise ValueError("starting_index must be non-negative.")

        extracted_images: list[ExtractedImage] = []
        seen_xrefs: set[int] = set()

        try:
            page_images = page.get_images(full=True)
        except Exception as exc:
            raise ImageExtractionError(
                f"Unable to inspect images on PDF page {page_number}."
            ) from exc

        for image_info in page_images:
            xref = image_info[0]

            # The same embedded image may be referenced multiple times
            # on a page. Store it only once for that page.
            if xref in seen_xrefs:
                continue

            seen_xrefs.add(xref)

            try:
                image_data = document.extract_image(xref)
            except Exception as exc:
                raise ImageExtractionError(
                    f"Unable to extract PDF image xref {xref} "
                    f"from page {page_number}."
                ) from exc

            image_bytes = image_data.get("image")

            if not image_bytes:
                raise InvalidImageError(
                    f"PDF image xref {xref} contains no image bytes."
                )

            extension = self._normalise_extension(
                image_data.get("ext", "png")
            )

            mime_type = (
                image_data.get("smask")
                and self._mime_type_from_extension(extension)
                or self._mime_type_from_extension(extension)
            )

            width = self._to_positive_int(
                image_data.get("width")
            )
            height = self._to_positive_int(
                image_data.get("height")
            )

            if width is None or height is None:
                detected_width, detected_height = (
                    self._read_image_dimensions(image_bytes)
                )
                width = width or detected_width
                height = height or detected_height

            image_index = starting_index + len(extracted_images)

            extracted_images.append(
                ExtractedImage(
                    image_index=image_index,
                    page_number=page_number,
                    file_name=(
                        f"page-{page_number}-image-"
                        f"{image_index}.{extension}"
                    ),
                    mime_type=mime_type,
                    image_bytes=image_bytes,
                    width=width,
                    height=height,
                    metadata={
                        "source_type": "pdf",
                        "xref": xref,
                        "extension": extension,
                    },
                )
            )

        return extracted_images

    def extract_from_docx(
        self,
        document: DOCXDocument,
        starting_index: int = 0,
    ) -> list[ExtractedImage]:
        """
        Extract embedded image parts from a DOCX document.

        DOCX does not reliably preserve page numbers, so page_number is None.
        """
        if starting_index < 0:
            raise ValueError("starting_index must be non-negative.")

        extracted_images: list[ExtractedImage] = []
        seen_part_names: set[str] = set()

        try:
            relationships = document.part.rels.values()
        except Exception as exc:
            raise ImageExtractionError(
                "Unable to inspect DOCX relationships."
            ) from exc

        for relationship in relationships:
            target_part = getattr(relationship, "target_part", None)

            if target_part is None:
                continue

            content_type = getattr(
                target_part,
                "content_type",
                "",
            )

            if not content_type.startswith("image/"):
                continue

            part_name = str(
                getattr(target_part, "partname", "")
            )

            if part_name in seen_part_names:
                continue

            seen_part_names.add(part_name)

            image_bytes = getattr(target_part, "blob", b"")

            if not image_bytes:
                raise InvalidImageError(
                    f"DOCX image part '{part_name}' has no bytes."
                )

            original_name = Path(part_name).name

            extension = self._extension_from_file_name(
                file_name=original_name,
                mime_type=content_type,
            )

            width, height = self._read_image_dimensions(
                image_bytes
            )

            image_index = starting_index + len(extracted_images)

            extracted_images.append(
                ExtractedImage(
                    image_index=image_index,
                    page_number=None,
                    paragraph_number=None,
                    file_name=(
                        original_name
                        or f"image-{image_index}.{extension}"
                    ),
                    mime_type=content_type,
                    image_bytes=image_bytes,
                    width=width,
                    height=height,
                    metadata={
                        "source_type": "docx",
                        "part_name": part_name,
                        "extension": extension,
                    },
                )
            )

        return extracted_images

    @staticmethod
    def _read_image_dimensions(
        image_bytes: bytes,
    ) -> tuple[int | None, int | None]:
        """Read image dimensions using Pillow when supported."""
        try:
            with Image.open(BytesIO(image_bytes)) as image:
                width, height = image.size
                return width, height
        except (UnidentifiedImageError, OSError):
            return None, None

    @staticmethod
    def _normalise_extension(extension: Any) -> str:
        """Normalise an image extension for file naming."""
        value = str(extension or "png").lower().lstrip(".")

        aliases = {
            "jpeg": "jpg",
            "jpe": "jpg",
        }

        return aliases.get(value, value)

    @classmethod
    def _mime_type_from_extension(
        cls,
        extension: str,
    ) -> str:
        """Resolve a MIME type from an image extension."""
        normalised = cls._normalise_extension(extension)

        explicit_types = {
            "jpg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "bmp": "image/bmp",
            "tif": "image/tiff",
            "tiff": "image/tiff",
            "webp": "image/webp",
            "jp2": "image/jp2",
        }

        if normalised in explicit_types:
            return explicit_types[normalised]

        guessed_type, _ = mimetypes.guess_type(
            f"image.{normalised}"
        )

        return guessed_type or "application/octet-stream"

    @classmethod
    def _extension_from_file_name(
        cls,
        file_name: str,
        mime_type: str,
    ) -> str:
        """Determine a usable extension from file name or MIME type."""
        suffix = Path(file_name).suffix

        if suffix:
            return cls._normalise_extension(suffix)

        guessed_extension = mimetypes.guess_extension(
            mime_type
        )

        if guessed_extension:
            return cls._normalise_extension(
                guessed_extension
            )

        return "bin"

    @staticmethod
    def _to_positive_int(
        value: Any,
    ) -> int | None:
        """Convert a value to a positive integer when possible."""
        try:
            converted = int(value)
        except (TypeError, ValueError):
            return None

        return converted if converted > 0 else None