"""Database configuration management."""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class DatabaseConfig:
    """Database connection configuration."""

    host: str
    port: int
    user: str
    password: str
    database: str
    pool_min_size: int = 10
    pool_max_size: int = 20
    pool_timeout: float = 30.0

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Load database configuration from environment variables."""
        return cls(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "postgres"),
            database=os.getenv("DB_NAME", "fte_db"),
            pool_min_size=int(os.getenv("DB_POOL_MIN_SIZE", "10")),
            pool_max_size=int(os.getenv("DB_POOL_MAX_SIZE", "20")),
            pool_timeout=float(os.getenv("DB_POOL_TIMEOUT", "30.0")),
        )

    def get_dsn(self) -> str:
        """Get PostgreSQL DSN connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    def validate(self) -> None:
        """Validate configuration values."""
        if not self.host:
            raise ValueError("DB_HOST is required")
        if not self.user:
            raise ValueError("DB_USER is required")
        if not self.password:
            raise ValueError("DB_PASSWORD is required")
        if not self.database:
            raise ValueError("DB_NAME is required")
        if self.pool_min_size < 1:
            raise ValueError("DB_POOL_MIN_SIZE must be at least 1")
        if self.pool_max_size < self.pool_min_size:
            raise ValueError("DB_POOL_MAX_SIZE must be >= DB_POOL_MIN_SIZE")
