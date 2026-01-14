"""
AI prompts extracted from n8n workflows
"""

from .article_generation import ARTICLE_GENERATION_PROMPT, RC_ARTICLE_PROMPT
from .article_validation import ARTICLE_VALIDATION_PROMPT
from .image_spec import IMAGE_SPEC_PROMPT
from .image_review import IMAGE_REVIEW_PROMPT
from .doubt_generation import DOUBT_GENERATION_PROMPT
from .doubt_response import GENUINE_DOUBT_RESPONSE_PROMPT, ALTERNATE_DOUBT_RESPONSE_PROMPT

__all__ = [
    "ARTICLE_GENERATION_PROMPT",
    "RC_ARTICLE_PROMPT",
    "ARTICLE_VALIDATION_PROMPT",
    "IMAGE_SPEC_PROMPT",
    "IMAGE_REVIEW_PROMPT",
    "DOUBT_GENERATION_PROMPT",
    "GENUINE_DOUBT_RESPONSE_PROMPT",
    "ALTERNATE_DOUBT_RESPONSE_PROMPT",
]
