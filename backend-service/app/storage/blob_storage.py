from abc import ABC, abstractmethod


class BlobStorage(ABC):
    """Interface for document and image blob storage."""

    @abstractmethod
    def list_blobs(
        self,
        container_name: str,
    ) -> list[str]:
        """Return all blob names in a container."""
        raise NotImplementedError

    @abstractmethod
    def download_blob(
        self,
        container_name: str,
        blob_name: str,
    ) -> bytes:
        """Download one blob."""
        raise NotImplementedError

    @abstractmethod
    def upload_blob(
        self,
        container_name: str,
        blob_name: str,
        data: bytes,
        content_type: str | None = None,
    ) -> str:
        """Upload one blob and return its stored name."""
        raise NotImplementedError