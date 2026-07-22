from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    app_name: str = Field(
        default="Agentic Engineering Knowledge Assistant",
        alias="APP_NAME",
    )
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")

    repository_type: str = Field(default="memory", alias="REPOSITORY_TYPE")
    top_k: int = Field(default=5, alias="TOP_K")

    database_url: str | None = Field(default=None, alias="DATABASE_URL")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    serper_api_key: str | None = Field(default=None, alias="SERPER_API_KEY")
    azure_storage_connection_string: str | None = Field(
        default=None,
        alias="AZURE_STORAGE_CONNECTION_STRING",
    )

    azure_original_documents_container: str = Field(
        default="original-documents",
        alias="AZURE_ORIGINAL_DOCUMENTS_CONTAINER",
    )

    azure_extracted_images_container: str = Field(
        default="extracted-images",
        alias="AZURE_EXTRACTED_IMAGES_CONTAINER",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Structure-aware Chunking
    # ------------------------------------------------------------------

    chunk_target_tokens: int = Field(
        default=500,
        alias="CHUNK_TARGET_TOKENS",
    )

    chunk_max_tokens: int = Field(
        default=700,
        alias="CHUNK_MAX_TOKENS",
    )

    chunk_overlap_tokens: int = Field(
        default=75,
        alias="CHUNK_OVERLAP_TOKENS",
    )

    retrieval_score_threshold: float = Field(
        default=0.75,
        alias="RETRIEVAL_SCORE_THRESHOLD",
    )

    web_search_top_k: int = Field(
        default=5,
        alias="WEB_SEARCH_TOP_K",
    )


@lru_cache
def get_settings() -> Settings:
    """Return one cached settings instance for the application."""
    return Settings()
