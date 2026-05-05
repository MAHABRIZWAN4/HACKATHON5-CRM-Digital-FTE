"""Health check endpoint."""

import os
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from app.db.connection import get_db_pool

router = APIRouter(tags=["health"])


@router.get("/", status_code=status.HTTP_200_OK)
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Support Ticket System API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "support": "/support",
            "webhooks": "/webhooks"
        }
    }


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint that verifies database connectivity."""
    disable_db = os.getenv("DISABLE_DB", "false").lower() == "true"

    if disable_db:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "healthy",
                "mode": "demo",
                "database": "disabled"
            }
        )

    try:
        # Check database connection
        db_pool = get_db_pool()
        await db_pool.fetchval("SELECT 1")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "healthy",
                "mode": "production",
                "database": "connected"
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "mode": "production",
                "database": "disconnected",
                "error": str(e)
            }
        )
