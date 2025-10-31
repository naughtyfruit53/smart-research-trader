"""Health check endpoint."""

from fastapi import APIRouter

from ...core.utils import get_version

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": get_version(),
    }
