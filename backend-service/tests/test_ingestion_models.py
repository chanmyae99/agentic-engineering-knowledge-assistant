from app.ingestion.models import (
    CaptionedImage,
    ExtractedImage,
    ParsedDocument,
    TextUnit,
)


text_unit = TextUnit(
    text="Workers must wear protective equipment.",
    page_number=1,
    section="Safety Requirements",
    paragraph_number=0,
)

image = ExtractedImage(
    image_index=0,
    file_name="page-1-image-0.png",
    mime_type="image/png",
    image_bytes=b"fake-image-bytes",
    page_number=1,
    width=640,
    height=480,
)

document = ParsedDocument(
    file_name="safety-manual.pdf",
    file_type="pdf",
    text_units=[text_unit],
    images=[image],
)

captioned_image = CaptionedImage(
    image=image,
    caption=(
        "A safety diagram showing workers wearing "
        "protective equipment."
    ),
    caption_model="vision-model",
)

print("FILE:", document.file_name)
print("TEXT UNITS:", len(document.text_units))
print("IMAGES:", len(document.images))
print("IMAGE PAGE:", document.images[0].page_number)
print("CAPTION:", captioned_image.caption)