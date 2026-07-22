import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from app.ingestion.caption_client import (
    OpenAIImageCaptionClient,
)
from app.ingestion.pdf_parser import PDFParser


load_dotenv()


async def main() -> None:
    file_path = Path("../documents/sample.pdf")

    parsed_document = PDFParser().parse(
        document_bytes=file_path.read_bytes(),
        file_name=file_path.name,
    )

    if not parsed_document.images:
        raise RuntimeError(
            "The PDF contains no extracted images."
        )

    # Select one larger image rather than a small logo.
    image = max(
        parsed_document.images,
        key=lambda item: (
            item.width or 0
        ) * (
            item.height or 0
        ),
    )

    client = OpenAIImageCaptionClient(
        api_key=os.getenv("OPENAI_API_KEY", ""),
        model=os.getenv(
            "OPENAI_VISION_MODEL",
            "gpt-4.1-mini",
        ),
        max_output_tokens=int(
            os.getenv(
                "IMAGE_CAPTION_MAX_OUTPUT_TOKENS",
                "200",
            )
        ),
        image_detail=os.getenv(
            "OPENAI_IMAGE_DETAIL",
            "high",
        ),
    )

    try:
        caption = await client.generate_caption(image)

        print("IMAGE:", image.file_name)
        print("PAGE:", image.page_number)
        print("SIZE:", image.width, "x", image.height)
        print("CAPTION:", caption)
    finally:
        await client.close()

    output_dir = Path("debug_images")
    output_dir.mkdir(exist_ok=True)

    with open(output_dir / image.file_name, "wb") as f:
        f.write(image.image_bytes)

    print("Saved:", output_dir / image.file_name)


if __name__ == "__main__":
    asyncio.run(main())
    from pathlib import Path



