import fitz

from app.ingestion.models import ParsedDocument, TextUnit


class PDFParser:
    """Extract page-level text and metadata from PDF documents."""

    def parse(
        self,
        document_bytes: bytes,
        file_name: str,
    ) -> ParsedDocument:
        text_units: list[TextUnit] = []

        with fitz.open(
            stream=document_bytes,
            filetype="pdf",
        ) as document:
            for page_index, page in enumerate(document):
                text = page.get_text("text").strip()

                if not text:
                    continue

                text_units.append(
                    TextUnit(
                        text=text,
                        page_number=page_index + 1,
                        metadata={
                            "source_type": "pdf",
                        },
                    )
                )

            metadata = {
                "page_count": document.page_count,
            }

        return ParsedDocument(
            file_name=file_name,
            file_type="pdf",
            text_units=text_units,
            metadata=metadata,
        )