"""
Articles API Router
"""

import asyncio
import logging
import uuid
from typing import Dict

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from app.agents.article_agent import ArticleAgent
from app.models.article import (
    ArticleGenerationRequest,
    ArticleGenerationResponse,
    ArticleStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory task storage (replace with Redis in production)
tasks: Dict[str, ArticleStatusResponse] = {}


@router.post("/generate", response_model=ArticleGenerationResponse)
async def generate_article(request: ArticleGenerationRequest):
    """
    Generate a new GMAT educational article.

    This endpoint generates an article from the provided collateral,
    validates it with Harvard-level review, and saves it to Airtable.
    """
    agent = ArticleAgent()

    result = await agent.generate_article(
        collateral=request.collateral,
        article_id=request.article_id,
    )

    if result.status == "error":
        raise HTTPException(status_code=500, detail=result.error_message)

    return result


@router.post("/generate/async")
async def generate_article_async(request: ArticleGenerationRequest):
    """
    Start async article generation and return a task ID.

    Use the task ID to check progress via /status/{task_id} or WebSocket.
    """
    task_id = str(uuid.uuid4())

    # Initialize task status
    tasks[task_id] = ArticleStatusResponse(
        task_id=task_id,
        status="pending",
        progress=0,
        current_step="Initializing...",
    )

    # Start background task
    asyncio.create_task(_generate_article_task(task_id, request))

    return {"task_id": task_id, "status": "started"}


async def _generate_article_task(task_id: str, request: ArticleGenerationRequest):
    """Background task for article generation"""
    agent = ArticleAgent()

    async def progress_callback(status: str, progress: int, step: str):
        tasks[task_id] = ArticleStatusResponse(
            task_id=task_id,
            status=status,
            progress=progress,
            current_step=step,
        )

    try:
        result = await agent.generate_article(
            collateral=request.collateral,
            article_id=request.article_id,
            progress_callback=progress_callback,
        )

        tasks[task_id] = ArticleStatusResponse(
            task_id=task_id,
            status="completed" if result.status == "success" else "error",
            progress=100,
            current_step="Complete" if result.status == "success" else "Failed",
            result=result,
            error_message=result.error_message,
        )

    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        tasks[task_id] = ArticleStatusResponse(
            task_id=task_id,
            status="error",
            progress=0,
            current_step="Failed",
            error_message=str(e),
        )


@router.get("/status/{task_id}", response_model=ArticleStatusResponse)
async def get_task_status(task_id: str):
    """Get the status of an article generation task"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks[task_id]


@router.get("/{article_id}")
async def get_article(article_id: str):
    """Get an article by ID"""
    agent = ArticleAgent()
    article = await agent.get_article_by_id(article_id)

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    return article


@router.get("/{article_id}/download")
async def download_article(article_id: str):
    """Download article as markdown file"""
    agent = ArticleAgent()
    article = await agent.get_article_by_id(article_id)

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    content = article.get("fields", {}).get("article_content_text", "")
    title = article.get("fields", {}).get("article_name", "article")

    # Clean filename
    filename = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
    filename = filename.replace(' ', '_')[:50]

    return StreamingResponse(
        iter([content.encode()]),
        media_type="text/markdown",
        headers={
            "Content-Disposition": f"attachment; filename={filename}.md"
        }
    )


@router.websocket("/ws/progress/{task_id}")
async def websocket_progress(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for real-time progress updates"""
    await websocket.accept()

    try:
        last_status = None

        while True:
            if task_id in tasks:
                current_status = tasks[task_id]

                # Send update if status changed
                if current_status != last_status:
                    await websocket.send_json(current_status.model_dump())
                    last_status = current_status

                    # Close if completed or errored
                    if current_status.status in ["completed", "error"]:
                        break

            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for task {task_id}")
