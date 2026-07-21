from typing import Any

from pydantic import BaseModel, Field


class IngestionRequest(BaseModel):
    blob_name: str = Field(
        min_length=1,
        description="Name of the source file in Azure Blob Storage.",
    )


class TextUnitResponse(BaseModel):
    text: str
    page_number: int | None = None
    section: str | None = None
    paragraph_number: int | None = None
    metadata: dict[str, Any]


class IngestionResponse(BaseModel):
    file_name: str
    file_type: str
    unit_count: int
    metadata: dict[str, Any]
    text_units: list[TextUnitResponse]