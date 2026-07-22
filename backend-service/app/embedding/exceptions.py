"""
Custom exceptions for the embedding module.
"""


class EmbeddingError(Exception):
    """
    Base class for all embedding-related errors.
    """


class EmbeddingConfigurationError(EmbeddingError):
    """
    Raised when the embedding service is improperly configured.

    Examples
    --------
    - Missing API key
    - Missing endpoint
    - Missing embedding model
    """


class EmbeddingGenerationError(EmbeddingError):
    """
    Raised when the embedding provider fails to generate embeddings.
    """


class EmbeddingDimensionError(EmbeddingError):
    """
    Raised when the returned embedding dimension
    does not match the expected dimension.
    """


class EmbeddingResponseError(EmbeddingError):
    """
    Raised when the embedding provider returns
    an unexpected or malformed response.
    """


class EmptyEmbeddingInputError(EmbeddingError):
    """
    Raised when an embedding request contains
    no valid text inputs.
    """