"""
OpenAI API client for image generation
"""

import base64
import logging
from typing import Optional
from openai import OpenAI, APIError
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Client for OpenAI API image generation"""

    def __init__(self):
        settings = get_settings()
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_image_model

    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "high",
        background: str = "opaque",
        n: int = 1,
    ) -> dict:
        """
        Generate an image using OpenAI's image generation API.

        Args:
            prompt: The image generation prompt
            size: Image size (e.g., "1024x1024")
            quality: Image quality ("high" or "standard")
            background: Background type ("opaque" or "transparent")
            n: Number of images to generate

        Returns:
            dict with 'b64_json' (base64 image data) and metadata
        """
        try:
            response = self.client.images.generate(
                model=self.model,
                prompt=prompt,
                n=n,
                size=size,
                quality=quality,
                response_format="b64_json",
            )

            return {
                "b64_json": response.data[0].b64_json,
                "revised_prompt": getattr(response.data[0], 'revised_prompt', None),
            }

        except APIError as e:
            logger.error(f"OpenAI image generation error: {e}")
            raise

    async def edit_image(
        self,
        image_bytes: bytes,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "high",
        input_fidelity: str = "low",
    ) -> dict:
        """
        Edit an existing image using OpenAI's image edit API.

        Args:
            image_bytes: Original image as bytes
            prompt: Edit instructions/prompt
            size: Output image size
            quality: Image quality
            input_fidelity: How closely to follow the input image

        Returns:
            dict with 'b64_json' (edited image data)
        """
        try:
            # Create a file-like object from bytes
            response = self.client.images.edit(
                model=self.model,
                image=image_bytes,
                prompt=prompt,
                n=1,
                size=size,
                response_format="b64_json",
            )

            return {
                "b64_json": response.data[0].b64_json,
            }

        except APIError as e:
            logger.error(f"OpenAI image edit error: {e}")
            raise

    async def generate_image_from_spec(
        self,
        image_spec: dict,
    ) -> dict:
        """
        Generate an image from a detailed specification.

        Args:
            image_spec: Full image specification from Claude

        Returns:
            dict with generated image data
        """
        # Build prompt from specification
        spec_prompt = self._build_prompt_from_spec(image_spec)

        # Determine size from spec
        dimensions = image_spec.get("detailed_specifications", {}).get("dimensions", "1024x1024")
        size = self._normalize_size(dimensions)

        return await self.generate_image(
            prompt=spec_prompt,
            size=size,
            quality="high",
        )

    def _build_prompt_from_spec(self, spec: dict) -> str:
        """Build an image generation prompt from specification"""
        detailed = spec.get("detailed_specifications", {})
        visual = detailed.get("visual_content", {})
        text_content = visual.get("text_content", {})
        colors = detailed.get("color_specifications", {})
        typography = detailed.get("typography", {})

        prompt_parts = [
            f"Create a professional {detailed.get('type', 'infographic')} image.",
            f"Purpose: {spec.get('purpose', 'Educational visualization')}",
        ]

        # Add visual elements
        elements = visual.get("primary_elements", [])
        if elements:
            prompt_parts.append(f"Include these elements: {', '.join(elements)}")

        # Add text content
        if text_content.get("headline"):
            prompt_parts.append(f"Headline text: \"{text_content['headline']}\"")

        labels = text_content.get("labels", [])
        if labels:
            prompt_parts.append(f"Labels: {', '.join(labels)}")

        # Add design specifications
        prompt_parts.append(f"Color scheme: Primary Blue #4A90E2, use clean professional colors")
        prompt_parts.append(f"Typography: Use Inter font family, clear hierarchy")
        prompt_parts.append("Style: Clean, modern, educational, WCAG 2.1 AA compliant")
        prompt_parts.append("Layout: Well-spaced using 8px grid system")

        return " ".join(prompt_parts)

    def _normalize_size(self, dimensions: str) -> str:
        """Normalize dimension string to valid OpenAI size"""
        valid_sizes = ["1024x1024", "1792x1024", "1024x1792"]

        # Try to extract dimensions
        if "1792" in dimensions or "landscape" in dimensions.lower():
            return "1792x1024"
        elif "portrait" in dimensions.lower():
            return "1024x1792"

        return "1024x1024"

    @staticmethod
    def base64_to_bytes(b64_string: str) -> bytes:
        """Convert base64 string to bytes"""
        return base64.b64decode(b64_string)

    @staticmethod
    def bytes_to_base64(data: bytes) -> str:
        """Convert bytes to base64 string"""
        return base64.b64encode(data).decode("utf-8")
