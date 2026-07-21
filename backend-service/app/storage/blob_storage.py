from abc import ABC, abstractmethod


class BlobStorage(ABC):
    """Storage contract used by the ingestion service."""

    @abstractmethod
    def download_blob(
        self,
        container_name: str,
        blob_name: str,
    ) -> bytes:
        """Download a blob and return its binary content."""
        raise NotImplementedError

    @abstractmethod
    def upload_blob(
        self,
        container_name: str,
        blob_name: str,
        data: bytes,
        content_type: str | None = None,
    ) -> str:
        """Upload binary data and return the stored blob name."""
        raise NotImplementedError