"""
Custom exceptions for the document ingestion pipeline.
"""


class IngestionError(Exception):
    """Base exception for ingestion-related failures."""


class DocumentParsingError(IngestionError):
    """Raised when a PDF or DOCX document cannot be parsed."""


class UnsupportedDocumentError(IngestionError):
    """Raised when the document type is not supported."""


class ImageExtractionError(IngestionError):
    """Raised when images cannot be extracted from a document."""


class CaptionGenerationError(IngestionError):
    """Raised when an image caption cannot be generated."""


class InvalidImageError(IngestionError):
    """Raised when extracted image data is missing or invalid."""


class EmptyDocumentError(IngestionError):
    """Raised when a parsed document contains no usable text or images."""