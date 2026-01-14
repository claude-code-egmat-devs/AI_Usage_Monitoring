"""
FastAPI routers
"""

from .articles import router as articles_router
from .images import router as images_router
from .doubts import router as doubts_router

__all__ = ["articles_router", "images_router", "doubts_router"]
