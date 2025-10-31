"""FastAPI application entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..core.config import settings
from ..core.logging import setup_logging
from .routes import health

# Setup logging
setup_logging()

# Create FastAPI app
app = FastAPI(
    title="Smart Research Trader API",
    description="AI-powered stock research and trading signals platform",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {"message": "Smart Research Trader API"}
