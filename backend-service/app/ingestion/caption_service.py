"""
Service for generating captions for extracted document images.
"""

from __future__ import annotations

from app.ingestion.caption_client import OpenAIImageCaptionClient
from app.ingestion.models import (
    CaptionedImage,
    ExtractedImage,
)


class CaptionService:
    """Generate captions for extracted images."""

    def __init__(
        self,
        caption_client: OpenAIImageCaptionClient,
    ) -> None:
        self._caption_client = caption_client

    async def caption_image(
        self,
        image: ExtractedImage,
    ) -> CaptionedImage:
        """
        Generate a caption for a single image.
        """
        caption = await self._caption_client.generate_caption(
            image=image,
        )

        return CaptionedImage(
            file_name=image.file_name,
            page_number=image.page_number,
            mime_type=image.mime_type,
            width=image.width,
            height=image.height,
            image_bytes=image.image_bytes,
            metadata=image.metadata,
            caption=caption,
        )

    async def caption_images(
        self,
        images: list[ExtractedImage],
    ) -> list[CaptionedImage]:
        """
        Generate captions for multiple images while preserving order.
        """
        captioned_images: list[CaptionedImage] = []

        for image in images:
            captioned_images.append(
                await self.caption_image(image)
            )

        return captioned_images