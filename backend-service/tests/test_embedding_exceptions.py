from app.embedding.exceptions import EmbeddingDimensionError

try:
    raise EmbeddingDimensionError("Wrong embedding dimension")
except EmbeddingDimensionError as e:
    print(type(e).__name__)
    print(e)