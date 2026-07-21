from app.ingestion.document_parser import DocumentParser
from app.ingestion.models import ParsedDocument
from app.storage.blob_storage import BlobStorage


class IngestionService:
    """Coordinates downloading and parsing source documents."""

    def __init__(
        self,
        blob_storage: BlobStorage,
        document_parser: DocumentParser,
        source_container: str,
    ) -> None:
        self._blob_storage = blob_storage
        self._document_parser = document_parser
        self._source_container = source_container

    def extract_document(
        self,
        blob_name: str,
    ) -> ParsedDocument:
        document_bytes = self._blob_storage.download_blob(
            container_name=self._source_container,
            blob_name=blob_name,
        )

        return self._document_parser.parse(
            document_bytes=document_bytes,
            file_name=blob_name,
        )