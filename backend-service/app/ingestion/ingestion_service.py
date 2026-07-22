from app.ingestion.caption_service import CaptionService
from app.ingestion.document_parser import DocumentParser
from app.ingestion.models import (
    CaptionedImage,
    ParsedDocument,
)
from app.storage.blob_storage import BlobStorage


class IngestionService:
    """Coordinates downloading, parsing and image captioning."""

    def __init__(
        self,
        blob_storage: BlobStorage,
        document_parser: DocumentParser,
        source_container: str,
        caption_service: CaptionService | None = None,
    ) -> None:
        self._blob_storage = blob_storage
        self._document_parser = document_parser
        self._source_container = source_container
        self._caption_service = caption_service

    def extract_document(
        self,
        blob_name: str,
    ) -> ParsedDocument:
        """
        Download and parse a source document.

        This method extracts text units and embedded images but does not
        generate image captions.
        """
        document_bytes = self._blob_storage.download_blob(
            container_name=self._source_container,
            blob_name=blob_name,
        )

        return self._document_parser.parse(
            document_bytes=document_bytes,
            file_name=blob_name,
        )

    async def extract_and_caption_document(
        self,
        blob_name: str,
    ) -> tuple[ParsedDocument, list[CaptionedImage]]:
        """
        Download and parse a document, then caption its extracted images.
        """
        parsed_document = self.extract_document(
            blob_name=blob_name,
        )

        if self._caption_service is None:
            raise RuntimeError(
                "CaptionService is required for image caption generation."
            )

        if not parsed_document.images:
            return parsed_document, []

        captioned_images = await self._caption_service.caption_images(
            images=parsed_document.images,
        )

        return parsed_document, captioned_images