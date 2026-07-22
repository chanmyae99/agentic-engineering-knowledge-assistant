"""
OpenAI client for generating searchable captions from extracted images.

The client is responsible only for:

- validating image input
- preparing the image for the OpenAI API
- submitting the caption request
- validating the provider response

Prompt wording is maintained separately in ``app.prompts``.
"""

from __future__ import annotations

import base64

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)

from app.ingestion.exceptions import (
    CaptionGenerationError,
    InvalidImageError,
)
from app.ingestion.models import ExtractedImage
from app.prompts.image_caption_prompts import IMAGE_CAPTION_PROMPT


class OpenAIImageCaptionClient:
    """Generate retrieval-friendly captions for document images."""

    SUPPORTED_MIME_TYPES = {
        "image/png",
        "image/jpeg",
        "image/webp",
        "image/gif",
    }

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4.1-mini",
        prompt: str = IMAGE_CAPTION_PROMPT,
        max_output_tokens: int = 200,
        image_detail: str = "low",
        timeout: float = 60.0,
        max_retries: int = 2,
    ) -> None:
        self.api_key = api_key.strip() if api_key else ""
        self.model = model.strip() if model else ""
        self.prompt = prompt.strip() if prompt else ""
        self.max_output_tokens = max_output_tokens
        self.image_detail = image_detail

        self._validate_configuration(
            timeout=timeout,
            max_retries=max_retries,
        )

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            timeout=timeout,
            max_retries=max_retries,
        )

    async def generate_caption(
        self,
        image: ExtractedImage,
    ) -> str:
        """Generate one searchable caption for an extracted image."""
        self._validate_image(image)

        image_data_url = self._build_data_url(
            image_bytes=image.image_bytes,
            mime_type=image.mime_type,
        )

        try:
            response = await self.client.responses.create(
                model=self.model,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": self.prompt,
                            },
                            {
                                "type": "input_image",
                                "image_url": image_data_url,
                                "detail": self.image_detail,
                            },
                        ],
                    }
                ],
                max_output_tokens=self.max_output_tokens,
            )

        except RateLimitError as exc:
            error_code = getattr(exc, "code", None)

            if error_code == "insufficient_quota":
                raise CaptionGenerationError(
                    "OpenAI API quota is unavailable. Check the "
                    "project billing balance and usage limits."
                ) from exc

            raise CaptionGenerationError(
                "The OpenAI image-caption request was rate limited."
            ) from exc

        except APITimeoutError as exc:
            raise CaptionGenerationError(
                "The OpenAI image-caption request timed out."
            ) from exc

        except APIConnectionError as exc:
            raise CaptionGenerationError(
                "Unable to connect to OpenAI for image captioning."
            ) from exc

        except APIStatusError as exc:
            raise CaptionGenerationError(
                "OpenAI returned an unsuccessful image-caption response "
                f"with status code {exc.status_code}."
            ) from exc

        except Exception as exc:
            raise CaptionGenerationError(
                "Unexpected failure while generating an image caption."
            ) from exc

        return self._extract_caption(
            response=response,
            file_name=image.file_name,
        )

    async def close(self) -> None:
        """Close the underlying asynchronous OpenAI client."""
        await self.client.close()

    def _validate_configuration(
        self,
        timeout: float,
        max_retries: int,
    ) -> None:
        """Validate the client configuration."""
        if not self.api_key:
            raise CaptionGenerationError(
                "OpenAI API key is required for image captioning."
            )

        if not self.model:
            raise CaptionGenerationError(
                "OpenAI vision model is required."
            )

        if not self.prompt:
            raise CaptionGenerationError(
                "Image-caption prompt must not be empty."
            )

        if self.max_output_tokens < 1:
            raise CaptionGenerationError(
                "max_output_tokens must be at least 1."
            )

        if self.image_detail not in {"low", "high", "auto"}:
            raise CaptionGenerationError(
                "image_detail must be 'low', 'high' or 'auto'."
            )

        if timeout <= 0:
            raise CaptionGenerationError(
                "timeout must be greater than zero."
            )

        if max_retries < 0:
            raise CaptionGenerationError(
                "max_retries cannot be negative."
            )

    def _validate_image(
        self,
        image: ExtractedImage,
    ) -> None:
        """Validate an image before submitting it to OpenAI."""
        if not isinstance(image, ExtractedImage):
            raise InvalidImageError(
                "image must be an ExtractedImage instance."
            )

        if not image.image_bytes:
            raise InvalidImageError(
                "Image bytes must not be empty."
            )

        if image.mime_type not in self.SUPPORTED_MIME_TYPES:
            raise InvalidImageError(
                "Unsupported image MIME type: "
                f"'{image.mime_type}'."
            )

    @staticmethod
    def _build_data_url(
        image_bytes: bytes,
        mime_type: str,
    ) -> str:
        """Convert image bytes into a Base64 data URL."""
        encoded_image = base64.b64encode(
            image_bytes
        ).decode("ascii")

        return f"data:{mime_type};base64,{encoded_image}"

    @staticmethod
    def _extract_caption(
        response: object,
        file_name: str,
    ) -> str:
        """Extract and validate caption text from an OpenAI response."""
        caption = getattr(response, "output_text", None)

        if not isinstance(caption, str) or not caption.strip():
            raise CaptionGenerationError(
                f"No caption was returned for image '{file_name}'."
            )

        return caption.strip()