"""FastAPI application entry point."""

import os
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.config import DatabaseConfig
from app.db.connection import init_db, close_db
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.api.routers import health, webhooks, support, dashboard

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

    # Check if database should be disabled (for Hugging Face Spaces)
    disable_db = os.getenv("DISABLE_DB", "false").lower() == "true"

    if not disable_db:
        try:
            # Initialize database
            db_config = DatabaseConfig.from_env()
            await init_db(db_config)
            logger.info("Database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            logger.warning("Running in demo mode without database")
    else:
        logger.info("Database disabled - running in demo mode")

    # Start Gmail polling as background task
    gmail_task = None
    if not disable_db:
        try:
            from app.handlers.gmail import gmail_handler
            if gmail_handler.config.polling_enabled:
                gmail_task = asyncio.create_task(gmail_handler.start_polling())
                logger.info("Gmail polling started")
            else:
                logger.info("Gmail polling disabled (set GMAIL_POLLING_ENABLED=true to enable)")
        except Exception as e:
            logger.warning(f"Could not start Gmail polling: {e}")

    yield

    # Shutdown
    logger.info("Shutting down application...")

    # Stop Gmail polling
    if gmail_task:
        try:
            from app.handlers.gmail import gmail_handler
            await gmail_handler.stop_polling()
            gmail_task.cancel()
            try:
                await gmail_task
            except asyncio.CancelledError:
                pass
            logger.info("Gmail polling stopped")
        except Exception as e:
            logger.warning(f"Error stopping Gmail polling: {e}")

    if not disable_db:
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
    app.include_router(dashboard.router)

    logger.info(f"Application created: {settings.app_name} v{settings.app_version}")

    return app


# Create app instance
app = create_app()
