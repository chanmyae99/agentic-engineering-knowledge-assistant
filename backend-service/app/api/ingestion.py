from fastapi import APIRouter, HTTPException, status

from app.core.config import get_settings
from app.ingestion.document_parser import (
    DocumentParser,
    UnsupportedDocumentTypeError,
)
from app.ingestion.ingestion_service import IngestionService
from app.schemas.ingestion import (
    IngestionRequest,
    IngestionResponse,
    TextUnitResponse,
)
from app.storage.azure_blob_storage import AzureBlobStorage

router = APIRouter(
    prefix="/ingestion",
    tags=["Ingestion"],
)


@router.post(
    "/extract",
    response_model=IngestionResponse,
)
def extract_document(
    request: IngestionRequest,
) -> IngestionResponse:
    settings = get_settings()

    try:
        blob_storage = AzureBlobStorage(
            settings.azure_storage_connection_string
        )

        service = IngestionService(
            blob_storage=blob_storage,
            document_parser=DocumentParser(),
            source_container=settings.azure_original_documents_container,
        )

        parsed_document = service.extract_document(request.blob_name)

        return IngestionResponse(
            file_name=parsed_document.file_name,
            file_type=parsed_document.file_type,
            unit_count=len(parsed_document.text_units),
            metadata=parsed_document.metadata,
            text_units=[
                TextUnitResponse(
                    text=unit.text,
                    page_number=unit.page_number,
                    section=unit.section,
                    paragraph_number=unit.paragraph_number,
                    metadata=unit.metadata,
                )
                for unit in parsed_document.text_units
            ],
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except UnsupportedDocumentTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc