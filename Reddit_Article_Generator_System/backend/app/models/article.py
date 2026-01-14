"""
Pydantic models for Article-related requests and responses
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field
from enum import Enum


class Section(str, Enum):
    """GMAT sections"""
    RC = "RC"
    CR = "CR"
    QUANT = "Quant"
    DI = "Data Insights"


class ArticleCollateral(BaseModel):
    """Input collateral for article generation"""
    passage_text: str = Field(..., description="The RC passage text")
    question_text: str = Field(..., description="The question text")
    question_stats: str = Field(..., description="Question statistics (accuracy, etc.)")
    detailed_solution: str = Field(..., description="Detailed solution explanation")
    popular_incorrect_choice: str = Field(..., description="Most common wrong answer chosen")
    section: Section = Field(..., description="GMAT section (RC, CR, Quant, DI)")


class ArticleGenerationRequest(BaseModel):
    """Request to generate an article"""
    collateral: ArticleCollateral
    article_id: Optional[str] = Field(None, description="Optional custom article ID")


class ArticleValidationResult(BaseModel):
    """Result of article validation"""
    article_title: str
    revised_article: str
    key_improvements_made: str
    final_rating: str
    final_rating_justification: str


class ArticleGenerationResponse(BaseModel):
    """Response from article generation"""
    article_id: str
    article_title: str
    article_content: str
    rating: str
    rating_justification: str
    section: Section
    status: Literal["success", "error"] = "success"
    error_message: Optional[str] = None


class ArticleStatusResponse(BaseModel):
    """Status of article generation task"""
    task_id: str
    status: Literal["pending", "generating", "validating", "completed", "error"]
    progress: int = Field(ge=0, le=100)
    current_step: str
    result: Optional[ArticleGenerationResponse] = None
    error_message: Optional[str] = None
