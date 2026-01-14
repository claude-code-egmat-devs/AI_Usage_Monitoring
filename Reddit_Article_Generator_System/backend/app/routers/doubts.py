"""
Doubts API Router - Placeholder
"""

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.post("/generate")
async def generate_doubts():
    """
    Generate doubts and responses for an article.

    TODO: Implement doubt generation pipeline
    """
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/status/{task_id}")
async def get_doubt_status(task_id: str):
    """Get status of doubt generation task"""
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/{article_id}")
async def get_article_doubts(article_id: str):
    """Get all doubts for an article"""
    raise HTTPException(status_code=501, detail="Not implemented yet")
