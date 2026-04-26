"""Shared pytest fixtures for all tests."""

import pytest
import pytest_asyncio
import os
from app.db.config import DatabaseConfig
from app.db.connection import DatabasePool


@pytest.fixture
def db_config():
    """Database configuration fixture."""
    return DatabaseConfig(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "fte_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        pool_min_size=2,
        pool_max_size=5,
        pool_timeout=10
    )


@pytest_asyncio.fixture
async def db_pool(db_config):
    """Database pool fixture."""
    pool = DatabasePool(db_config)
    await pool.connect()
    yield pool
    await pool.disconnect()
