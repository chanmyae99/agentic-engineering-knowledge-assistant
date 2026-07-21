from pathlib import Path

from app.ingestion.docx_parser import DOCXParser
from app.ingestion.models import ParsedDocument
from app.ingestion.pdf_parser import PDFParser


class UnsupportedDocumentTypeError(ValueError):
    """Raised when the document format is not supported."""


class DocumentParser:
    """Select the correct parser based on the file extension."""

    def __init__(self) -> None:
        self._pdf_parser = PDFParser()
        self._docx_parser = DOCXParser()

    def parse(
        self,
        document_bytes: bytes,
        file_name: str,
    ) -> ParsedDocument:
        extension = Path(file_name).suffix.lower()

        if extension == ".pdf":
            return self._pdf_parser.parse(document_bytes, file_name)

        if extension == ".docx":
            return self._docx_parser.parse(document_bytes, file_name)

        raise UnsupportedDocumentTypeError(
            f"Unsupported document type: '{extension}'. "
            "Supported types are PDF and DOCX."
        )