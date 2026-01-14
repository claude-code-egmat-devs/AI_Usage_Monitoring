"""
Article Generation and Validation Agent
"""

import json
import logging
import uuid
from typing import Optional

from app.config import get_settings
from app.services.anthropic_client import AnthropicClient
from app.services.airtable_client import AirtableClient
from app.models.article import (
    ArticleCollateral,
    ArticleGenerationResponse,
    ArticleValidationResult,
    Section,
)
from app.prompts.article_generation import get_article_generation_prompt, RC_ARTICLE_PROMPT
from app.prompts.article_validation import get_validation_prompt

logger = logging.getLogger(__name__)


class ArticleAgent:
    """Agent for generating and validating GMAT educational articles"""

    def __init__(self):
        self.anthropic = AnthropicClient()
        self.airtable = AirtableClient()
        self.settings = get_settings()

    async def generate_article(
        self,
        collateral: ArticleCollateral,
        article_id: Optional[str] = None,
        progress_callback: Optional[callable] = None,
    ) -> ArticleGenerationResponse:
        """
        Generate and validate an article from the provided collateral.

        Args:
            collateral: Input collateral (passage, question, stats, solution, incorrect choice)
            article_id: Optional custom article ID
            progress_callback: Optional callback for progress updates

        Returns:
            ArticleGenerationResponse with generated article and rating
        """
        article_id = article_id or f"ART-{uuid.uuid4().hex[:8].upper()}"

        try:
            # Step 1: Generate initial article
            if progress_callback:
                await progress_callback("generating", 10, "Generating initial article...")

            generated = await self._generate_initial_article(collateral)

            if not generated.get("parsed"):
                raise ValueError(f"Failed to parse article generation response: {generated.get('parse_error')}")

            initial_article = generated["parsed"]["generated_article"]
            analysis = generated["parsed"]["analysis_and_approach"]

            logger.info(f"Initial article generated for {article_id}")

            # Step 2: Validate and improve article
            if progress_callback:
                await progress_callback("validating", 50, "Validating article with Harvard-level review...")

            validated = await self._validate_article(
                article=initial_article,
                collateral=collateral,
            )

            if not validated.get("parsed"):
                raise ValueError(f"Failed to parse validation response: {validated.get('parse_error')}")

            validation_result = ArticleValidationResult(**validated["parsed"])

            logger.info(f"Article validated for {article_id}, rating: {validation_result.final_rating}")

            # Step 3: Save to Airtable
            if progress_callback:
                await progress_callback("saving", 90, "Saving to database...")

            await self.airtable.create_article_input(
                article_id=article_id,
                article_name=validation_result.article_title,
                article_section=collateral.section.value,
                article_content=validation_result.revised_article,
                article_rating=validation_result.final_rating,
                rating_justification=validation_result.final_rating_justification,
            )

            if progress_callback:
                await progress_callback("completed", 100, "Article generation complete!")

            return ArticleGenerationResponse(
                article_id=article_id,
                article_title=validation_result.article_title,
                article_content=validation_result.revised_article,
                rating=validation_result.final_rating,
                rating_justification=validation_result.final_rating_justification,
                section=collateral.section,
                status="success",
            )

        except Exception as e:
            logger.error(f"Article generation failed for {article_id}: {e}")
            return ArticleGenerationResponse(
                article_id=article_id,
                article_title="",
                article_content="",
                rating="0",
                rating_justification="",
                section=collateral.section,
                status="error",
                error_message=str(e),
            )

    async def _generate_initial_article(
        self,
        collateral: ArticleCollateral,
    ) -> dict:
        """Generate the initial article using Claude"""

        # Build the prompt based on section
        if collateral.section == Section.RC:
            prompt = get_article_generation_prompt(
                passage_text=collateral.passage_text,
                question_text=collateral.question_text,
                question_stats=collateral.question_stats,
                detailed_solution=collateral.detailed_solution,
                popular_incorrect_choice=collateral.popular_incorrect_choice,
            )
        else:
            # For other sections, use a more generic approach
            reference = f"""Passage/Question Text:
{collateral.passage_text}

Question Text:
{collateral.question_text}

Question Stats:
{collateral.question_stats}

Detailed Solution:
{collateral.detailed_solution}

Popular Incorrect Choice:
{collateral.popular_incorrect_choice}"""

            prompt = f"""You are an expert GMAT educator creating educational articles for the {collateral.section.value} section.

Reference Material:
{reference}

Create an educational article that:
1. Starts with a generic, engaging hook
2. Explains why students make this mistake
3. Provides a clear framework to avoid the mistake
4. Includes practice exercises

OUTPUT FORMAT:
Return a JSON object with exactly these two attributes:
{{
  "analysis_and_approach": "Your analysis and teaching strategy",
  "generated_article": "The complete article text"
}}"""

        output_schema = {
            "analysis_and_approach": "Detailed analysis",
            "generated_article": "Complete article text"
        }

        return await self.anthropic.generate_structured(
            prompt=prompt,
            output_schema=output_schema,
            thinking_budget=self.settings.thinking_budget,
        )

    async def _validate_article(
        self,
        article: str,
        collateral: ArticleCollateral,
    ) -> dict:
        """Validate the article using Harvard-level review"""

        reference_questions = f"""Passage Text:
{collateral.passage_text}

Question Text:
{collateral.question_text}

Question Stats:
{collateral.question_stats}

Detailed Solution:
{collateral.detailed_solution}

Popular Incorrect Choice:
{collateral.popular_incorrect_choice}"""

        prompt = get_validation_prompt(
            article=article,
            reference_questions=reference_questions,
        )

        output_schema = {
            "article_title": "Title of the article",
            "revised_article": "The revised article content",
            "key_improvements_made": "Description of improvements",
            "final_rating": "85",
            "final_rating_justification": "Justification for the rating"
        }

        return await self.anthropic.generate_structured(
            prompt=prompt,
            output_schema=output_schema,
            thinking_budget=self.settings.thinking_budget,
        )

    async def get_article_by_id(self, article_id: str) -> Optional[dict]:
        """Retrieve an article by its ID from Airtable"""
        records = await self.airtable.search_article_input(article_id=article_id)
        return records[0] if records else None
