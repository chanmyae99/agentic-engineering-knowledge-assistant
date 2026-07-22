import fitz

from app.ingestion.image_extractor import ImageExtractor
from app.ingestion.models import (
    ExtractedImage,
    ParsedDocument,
    TextUnit,
)


class PDFParser:
    """Extract text, images and metadata from PDF documents."""

    def __init__(
        self,
        image_extractor: ImageExtractor | None = None,
    ) -> None:
        self._image_extractor = (
            image_extractor or ImageExtractor()
        )

    def parse(
        self,
        document_bytes: bytes,
        file_name: str,
    ) -> ParsedDocument:
        text_units: list[TextUnit] = []
        images: list[ExtractedImage] = []

        with fitz.open(
            stream=document_bytes,
            filetype="pdf",
        ) as document:
            for page_index, page in enumerate(document):
                page_number = page_index + 1
                text = page.get_text("text").strip()

                # Do not continue when text is empty because the page
                # may still contain useful images.
                if text:
                    text_units.append(
                        TextUnit(
                            text=text,
                            page_number=page_number,
                            metadata={
                                "source_type": "pdf",
                            },
                        )
                    )

                page_images = (
                    self._image_extractor
                    .extract_from_pdf_page(
                        document=document,
                        page=page,
                        page_number=page_number,
                        starting_index=len(images),
                    )
                )

                images.extend(page_images)

            metadata = {
                "page_count": document.page_count,
                "image_count": len(images),
            }

        return ParsedDocument(
            file_name=file_name,
            file_type="pdf",
            text_units=text_units,
            images=images,
            metadata=metadata,
        )