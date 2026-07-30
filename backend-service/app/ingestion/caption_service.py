"""
Service for generating captions for extracted document images.
"""

from __future__ import annotations

from app.ingestion.caption_client import OpenAIImageCaptionClient
from app.ingestion.models import CaptionedImage, ExtractedImage
from app.ingestion.exceptions import InvalidImageError


class CaptionService:
    """Generate captions for extracted images."""

    def __init__(
        self,
        caption_client: OpenAIImageCaptionClient,
        caption_model: str = "gpt-4.1-mini",
    ) -> None:
        if not caption_model.strip():
            raise ValueError("caption_model must not be empty.")

        self._caption_client = caption_client
        self._caption_model = caption_model

    async def caption_image(
        self,
        image: ExtractedImage,
    ) -> CaptionedImage:
        """Generate a caption for a single image."""
        caption = await self._caption_client.generate_caption(
            image=image,
        )

        return CaptionedImage(
            image=image,
            caption=caption,
            caption_model=self._caption_model,
            metadata={
                **image.metadata,
                "caption_model": self._caption_model,
            },
        )

    async def caption_images(
        self,
        images: list[ExtractedImage],
    ) -> list[CaptionedImage]:
        """Generate captions while preserving image order."""
        captioned_images: list[CaptionedImage] = []

        for image in images:
            try:
                captioned_images.append(
                    await self.caption_image(image)
                )
            except InvalidImageError as exc:
                print(
                    f"Skipping image '{image.file_name}': {exc}"
                )

        return captioned_images