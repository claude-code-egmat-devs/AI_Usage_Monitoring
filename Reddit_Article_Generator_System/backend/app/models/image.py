"""
Pydantic models for Image-related requests and responses
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field


class ImageSpec(BaseModel):
    """Specification for a single image"""
    image_number: int
    descriptive_name: str
    placement: str
    purpose: str
    priority: Literal["Critical", "High", "Medium", "Low"]
    detailed_specifications: dict  # Full spec from Claude


class ImageGenerationRequest(BaseModel):
    """Request to generate images for an article"""
    article_id: str
    article_name: str
    article_content: str


class GeneratedImage(BaseModel):
    """A generated image with metadata"""
    image_number: int
    descriptive_name: str
    placement: str
    local_path: Optional[str] = None  # Temporary local path
    drive_url: Optional[str] = None  # Google Drive URL
    drive_file_id: Optional[str] = None
    changes_required: bool = False
    changes_details: Optional[list] = None
    status: Literal["pending", "generated", "reviewed", "fixed", "uploaded", "error"] = "pending"
    error_message: Optional[str] = None


class ImageGenerationResponse(BaseModel):
    """Response from image generation"""
    article_id: str
    article_name: str
    images: list[GeneratedImage]
    drive_folder_url: Optional[str] = None
    drive_folder_id: Optional[str] = None
    status: Literal["success", "partial", "error"] = "success"
    total_images: int
    successful_images: int
    error_message: Optional[str] = None


class ImageStatusResponse(BaseModel):
    """Status of image generation task"""
    task_id: str
    status: Literal["pending", "generating_specs", "generating_images", "reviewing", "fixing", "uploading", "completed", "error"]
    progress: int = Field(ge=0, le=100)
    current_step: str
    current_image: Optional[int] = None
    total_images: Optional[int] = None
    result: Optional[ImageGenerationResponse] = None
    error_message: Optional[str] = None


class ImageReviewResult(BaseModel):
    """Result of image review"""
    changes_required: Literal["YES", "NO"]
    changes_count: int
    changes_details: list[dict]
