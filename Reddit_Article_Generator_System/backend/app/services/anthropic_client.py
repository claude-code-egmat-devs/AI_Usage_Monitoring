"""
Anthropic Claude API client for article generation and validation
"""

import json
import logging
from typing import Optional, Any
from anthropic import Anthropic, APIError

from app.config import get_settings

logger = logging.getLogger(__name__)


class AnthropicClient:
    """Client for Anthropic Claude API with extended thinking support"""

    def __init__(self):
        settings = get_settings()
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model
        self.thinking_budget = settings.thinking_budget
        self.max_tokens = settings.max_tokens

    async def generate_with_thinking(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        thinking_budget: Optional[int] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 1.0,  # Required for extended thinking
    ) -> dict[str, Any]:
        """
        Generate content using Claude with extended thinking enabled.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            thinking_budget: Token budget for thinking (default from config)
            max_tokens: Max output tokens (default from config)
            temperature: Temperature setting (must be 1.0 for extended thinking)

        Returns:
            dict with 'thinking', 'content', and 'usage' keys
        """
        thinking_budget = thinking_budget or self.thinking_budget
        max_tokens = max_tokens or self.max_tokens

        messages = [{"role": "user", "content": prompt}]

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                thinking={
                    "type": "enabled",
                    "budget_tokens": thinking_budget
                },
                system=system_prompt or "",
                messages=messages
            )

            # Extract thinking and content from response
            thinking_content = ""
            text_content = ""

            for block in response.content:
                if block.type == "thinking":
                    thinking_content = block.thinking
                elif block.type == "text":
                    text_content = block.text

            return {
                "thinking": thinking_content,
                "content": text_content,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                }
            }

        except APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise

    async def generate_structured(
        self,
        prompt: str,
        output_schema: dict,
        system_prompt: Optional[str] = None,
        thinking_budget: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Generate structured JSON output using Claude.

        Args:
            prompt: The user prompt
            output_schema: JSON schema example for output format
            system_prompt: Optional system prompt
            thinking_budget: Token budget for thinking

        Returns:
            Parsed JSON response
        """
        # Append JSON schema instructions to prompt
        schema_instruction = f"""

Your response must be valid JSON matching this structure:
```json
{json.dumps(output_schema, indent=2)}
```

Return ONLY the JSON object, no additional text."""

        full_prompt = prompt + schema_instruction

        result = await self.generate_with_thinking(
            prompt=full_prompt,
            system_prompt=system_prompt,
            thinking_budget=thinking_budget,
        )

        # Parse JSON from content
        content = result["content"].strip()

        # Handle markdown code blocks
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        try:
            parsed = json.loads(content.strip())
            result["parsed"] = parsed
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Raw content: {content[:500]}")
            result["parsed"] = None
            result["parse_error"] = str(e)
            return result

    async def generate_simple(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> str:
        """
        Simple generation without extended thinking.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            max_tokens: Max output tokens

        Returns:
            Generated text content
        """
        messages = [{"role": "user", "content": prompt}]

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt or "",
                messages=messages
            )

            return response.content[0].text

        except APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise

    async def review_image(
        self,
        image_base64: str,
        image_spec: dict,
        review_prompt: str,
    ) -> dict[str, Any]:
        """
        Review an image using Claude's vision capabilities.

        Args:
            image_base64: Base64 encoded image
            image_spec: Original image specification
            review_prompt: The review prompt

        Returns:
            Review result with changes if needed
        """
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Original Image Specification:\n{json.dumps(image_spec, indent=2)}\n\n{review_prompt}"
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_base64
                        }
                    }
                ]
            }
        ]

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=1.0,
                thinking={
                    "type": "enabled",
                    "budget_tokens": self.thinking_budget
                },
                messages=messages
            )

            # Extract content
            text_content = ""
            for block in response.content:
                if block.type == "text":
                    text_content = block.text

            # Parse JSON response
            content = text_content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            return json.loads(content.strip())

        except APIError as e:
            logger.error(f"Anthropic API error during image review: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse image review response: {e}")
            return {
                "changes_required": "NO",
                "changes_count": 0,
                "changes_details": [],
                "parse_error": str(e)
            }
