from app.ingestion.exceptions import ImageExtractionError


try:
    raise ImageExtractionError("Unable to extract image.")
except ImageExtractionError as error:
    print(type(error).__name__)
    print(error)