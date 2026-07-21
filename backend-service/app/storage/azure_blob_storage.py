from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient, ContentSettings

from app.storage.blob_storage import BlobStorage


class AzureBlobStorage(BlobStorage):
    """Azure Blob Storage implementation."""

    def __init__(self, connection_string: str) -> None:
        if not connection_string:
            raise ValueError(
                "AZURE_STORAGE_CONNECTION_STRING is not configured."
            )

        self._service_client = BlobServiceClient.from_connection_string(
            connection_string
        )

    def download_blob(
        self,
        container_name: str,
        blob_name: str,
    ) -> bytes:
        blob_client = self._service_client.get_blob_client(
            container=container_name,
            blob=blob_name,
        )

        try:
            return blob_client.download_blob().readall()
        except ResourceNotFoundError as exc:
            raise FileNotFoundError(
                f"Blob '{blob_name}' was not found in "
                f"container '{container_name}'."
            ) from exc

    def upload_blob(
        self,
        container_name: str,
        blob_name: str,
        data: bytes,
        content_type: str | None = None,
    ) -> str:
        blob_client = self._service_client.get_blob_client(
            container=container_name,
            blob=blob_name,
        )

        content_settings = None
        if content_type:
            content_settings = ContentSettings(content_type=content_type)

        blob_client.upload_blob(
            data,
            overwrite=True,
            content_settings=content_settings,
        )

        return blob_name