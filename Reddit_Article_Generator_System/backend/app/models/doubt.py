"""
Pydantic models for Doubt-related requests and responses
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field


class Doubt(BaseModel):
    """A generated student doubt"""
    doubt_number: int
    doubt_category: Literal["GENUINE", "ALTERNATE"]
    logical_gap_number: str
    student_level: Literal["Low", "Medium", "High"]
    doubt_text: str
    student_reasoning: str


class DoubtResponse(BaseModel):
    """Response to a doubt"""
    doubt_number: int
    doubt_category: Literal["GENUINE", "ALTERNATE"]
    analysis: str
    exception_flag: bool = False
    exception_reason: Optional[str] = None
    response: str


class DoubtGenerationRequest(BaseModel):
    """Request to generate doubts for an article"""
    article_id: str
    article_name: str
    article_content: str
    section: str


class DoubtGenerationResponse(BaseModel):
    """Response from doubt generation"""
    article_id: str
    article_name: str
    gmat_sub_section: str
    logical_gaps: list[str]
    gap_to_category_mapping: str
    doubts: list[Doubt]
    responses: list[DoubtResponse]
    status: Literal["success", "partial", "error"] = "success"
    error_message: Optional[str] = None


class DoubtStatusResponse(BaseModel):
    """Status of doubt generation task"""
    task_id: str
    status: Literal["pending", "analyzing", "generating_doubts", "generating_responses", "completed", "error"]
    progress: int = Field(ge=0, le=100)
    current_step: str
    current_doubt: Optional[int] = None
    total_doubts: int = 5
    result: Optional[DoubtGenerationResponse] = None
    error_message: Optional[str] = None
