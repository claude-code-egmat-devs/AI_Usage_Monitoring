"""
Images API Router - Placeholder
"""

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.post("/generate")
async def generate_images():
    """
    Generate images for an article.

    TODO: Implement image generation pipeline
    """
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/status/{task_id}")
async def get_image_status(task_id: str):
    """Get status of image generation task"""
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/{article_id}")
async def get_article_images(article_id: str):
    """Get all images for an article"""
    raise HTTPException(status_code=501, detail="Not implemented yet")
