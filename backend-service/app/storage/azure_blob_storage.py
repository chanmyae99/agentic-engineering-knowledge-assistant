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

        self._service_client = (
            BlobServiceClient.from_connection_string(
                connection_string
            )
        )

    def list_blobs(
        self,
        container_name: str,
    ) -> list[str]:
        """
        Return the names of all blobs in a container.

        Folder-like paths are preserved, for example:
        ``guidelines/safety-guide.pdf``.
        """
        if not container_name or not container_name.strip():
            raise ValueError(
                "container_name must not be empty."
            )

        container_client = (
            self._service_client.get_container_client(
                container=container_name.strip(),
            )
        )

        try:
            return [
                blob.name
                for blob in container_client.list_blobs()
            ]
        except ResourceNotFoundError as exc:
            raise FileNotFoundError(
                f"Container '{container_name}' was not found."
            ) from exc

    def download_blob(
        self,
        container_name: str,
        blob_name: str,
    ) -> bytes:
        """Download one blob and return its bytes."""
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
        """
        Upload bytes to Azure Blob Storage.

        Existing blobs with the same name are replaced.
        """
        blob_client = self._service_client.get_blob_client(
            container=container_name,
            blob=blob_name,
        )

        content_settings = None

        if content_type:
            content_settings = ContentSettings(
                content_type=content_type,
            )

        blob_client.upload_blob(
            data,
            overwrite=True,
            content_settings=content_settings,
        )

        return blob_name