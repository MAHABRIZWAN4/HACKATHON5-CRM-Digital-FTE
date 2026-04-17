"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.config import DatabaseConfig
from app.db.connection import init_db, close_db
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.api.routers import health, webhooks, support

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting application...")

    try:
        # Initialize database
        db_config = DatabaseConfig.from_env()
        await init_db(db_config)
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down application...")
    await close_db()
    logger.info("Database closed")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add error handling middleware
    app.add_middleware(ErrorHandlerMiddleware)

    # Include routers
    app.include_router(health.router)
    app.include_router(webhooks.router)
    app.include_router(support.router)

    logger.info(f"Application created: {settings.app_name} v{settings.app_version}")

    return app


# Create app instance
app = create_app()
