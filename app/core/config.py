"""Application configuration from environment variables."""

import os
from typing import List


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        self.app_name: str = os.getenv("APP_NAME", "FTE Support System")
        self.app_version: str = os.getenv("APP_VERSION", "1.0.0")
        self.debug: bool = os.getenv("DEBUG", "false").lower() == "true"

        # CORS settings
        cors_origins = os.getenv("CORS_ORIGINS", "*")
        self.cors_origins: List[str] = [
            origin.strip() for origin in cors_origins.split(",")
        ]

        # API settings
        self.api_prefix: str = os.getenv("API_PREFIX", "")

    def validate(self) -> None:
        """Validate configuration."""
        if not self.app_name:
            raise ValueError("APP_NAME cannot be empty")


def get_settings() -> Settings:
    """Get application settings."""
    settings = Settings()
    settings.validate()
    return settings
