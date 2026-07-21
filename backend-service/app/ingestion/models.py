from dataclasses import dataclass, field
from typing import Any


@dataclass
class TextUnit:
    """Structured text extracted from one document location."""

    text: str
    page_number: int | None = None
    section: str | None = None
    paragraph_number: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedDocument:
    """Result returned by a document parser."""

    file_name: str
    file_type: str
    text_units: list[TextUnit]
    metadata: dict[str, Any] = field(default_factory=dict)