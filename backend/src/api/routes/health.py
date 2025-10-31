"""Health check endpoint."""

from fastapi import APIRouter

from ...core.utils import get_version
from ...db.session import check_db_health

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    db_healthy = check_db_health()
    return {
        "status": "ok" if db_healthy else "degraded",
        "version": get_version(),
        "database": "connected" if db_healthy else "disconnected",
    }
