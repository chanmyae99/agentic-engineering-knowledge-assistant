from pathlib import Path

from app.ingestion.docx_parser import DOCXParser
from app.ingestion.exceptions import UnsupportedDocumentError
from app.ingestion.models import ParsedDocument
from app.ingestion.pdf_parser import PDFParser


class DocumentParser:
    """Select the correct parser based on the file extension."""

    def __init__(
        self,
        pdf_parser: PDFParser | None = None,
        docx_parser: DOCXParser | None = None,
    ) -> None:
        self._pdf_parser = pdf_parser or PDFParser()
        self._docx_parser = docx_parser or DOCXParser()

    def parse(
        self,
        document_bytes: bytes,
        file_name: str,
    ) -> ParsedDocument:
        if not document_bytes:
            raise ValueError("document_bytes must not be empty.")

        if not file_name or not file_name.strip():
            raise ValueError("file_name must not be empty.")

        extension = Path(file_name).suffix.lower()

        if extension == ".pdf":
            return self._pdf_parser.parse(
                document_bytes=document_bytes,
                file_name=file_name,
            )

        if extension == ".docx":
            return self._docx_parser.parse(
                document_bytes=document_bytes,
                file_name=file_name,
            )

        raise UnsupportedDocumentError(
            f"Unsupported document type: '{extension}'. "
            "Supported types are PDF and DOCX."
        )