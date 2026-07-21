from azure.storage.blob import BlobServiceClient

from app.core.config import get_settings


def main() -> None:
    settings = get_settings()

    connection_string = settings.azure_storage_connection_string
    container_name = settings.azure_original_documents_container

    if not connection_string:
        raise RuntimeError(
            "AZURE_STORAGE_CONNECTION_STRING is missing from .env"
        )

    service_client = BlobServiceClient.from_connection_string(
        connection_string
    )

    container_client = service_client.get_container_client(
        container_name
    )

    print(f"Connected to container: {container_name}")
    print("Available blobs:")

    blob_count = 0

    for blob in container_client.list_blobs():
        print(f"- {blob.name}")
        blob_count += 1

        if blob_count >= 30:
            print("Showing only the first 30 blobs.")
            break

    if blob_count == 0:
        print("Connected successfully, but no blobs were found.")


if __name__ == "__main__":
    main()