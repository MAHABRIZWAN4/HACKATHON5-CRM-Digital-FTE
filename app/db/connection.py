"""Async database connection pool management."""

import asyncpg
import logging
from typing import Optional
from contextlib import asynccontextmanager

from app.db.config import DatabaseConfig

logger = logging.getLogger(__name__)


class DatabasePool:
    """Manages asyncpg connection pool lifecycle."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """Initialize the connection pool."""
        if self._pool is not None:
            logger.warning("Database pool already initialized")
            return

        try:
            self.config.validate()
            logger.info(
                f"Connecting to database: {self.config.host}:{self.config.port}/{self.config.database}"
            )

            self._pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                min_size=self.config.pool_min_size,
                max_size=self.config.pool_max_size,
                timeout=self.config.pool_timeout,
                command_timeout=60.0,
            )

            logger.info(
                f"Database pool initialized: min={self.config.pool_min_size}, max={self.config.pool_max_size}"
            )

        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def disconnect(self) -> None:
        """Close the connection pool."""
        if self._pool is None:
            logger.warning("Database pool not initialized")
            return

        try:
            logger.info("Closing database pool")
            await self._pool.close()
            self._pool = None
            logger.info("Database pool closed")
        except Exception as e:
            logger.error(f"Error closing database pool: {e}")
            raise

    @asynccontextmanager
    async def acquire(self):
        """Acquire a connection from the pool."""
        if self._pool is None:
            raise RuntimeError("Database pool not initialized. Call connect() first.")

        async with self._pool.acquire() as connection:
            yield connection

    async def execute(self, query: str, *args) -> str:
        """Execute a query and return status."""
        async with self.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args) -> list:
        """Fetch multiple rows."""
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Fetch a single row."""
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        """Fetch a single value."""
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args)

    @property
    def pool(self) -> asyncpg.Pool:
        """Get the underlying pool (for advanced usage)."""
        if self._pool is None:
            raise RuntimeError("Database pool not initialized")
        return self._pool


# Global database pool instance
_db_pool: Optional[DatabasePool] = None


def get_db_pool() -> DatabasePool:
    """Get the global database pool instance."""
    global _db_pool
    if _db_pool is None:
        raise RuntimeError("Database pool not initialized. Call init_db() first.")
    return _db_pool


async def init_db(config: Optional[DatabaseConfig] = None) -> DatabasePool:
    """Initialize the global database pool."""
    global _db_pool

    if _db_pool is not None:
        logger.warning("Database pool already initialized")
        return _db_pool

    if config is None:
        config = DatabaseConfig.from_env()

    _db_pool = DatabasePool(config)
    await _db_pool.connect()
    return _db_pool


async def close_db() -> None:
    """Close the global database pool."""
    global _db_pool

    if _db_pool is None:
        logger.warning("Database pool not initialized")
        return

    await _db_pool.disconnect()
    _db_pool = None
