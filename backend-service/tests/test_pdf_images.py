from pathlib import Path

from app.ingestion.pdf_parser import PDFParser

file_path = Path("../documents/sample.pdf")

document = PDFParser().parse(
    document_bytes=file_path.read_bytes(),
    file_name=file_path.name,
)

print("FILE:", document.file_name)
print("TEXT UNITS:", len(document.text_units))
print("IMAGES:", len(document.images))
print("METADATA:", document.metadata)

for image in document.images:
    print(
        image.image_index,
        image.page_number,
        image.file_name,
        image.mime_type,
        image.width,
        image.height,
        len(image.image_bytes),
    )