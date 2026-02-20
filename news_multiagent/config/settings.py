"""
Application settings using Pydantic BaseSettings.

Manages configuration from environment variables with validation and defaults.
"""

from functools import lru_cache
from typing import List, Optional
from pydantic import BaseSettings, Field, validator
import os


class Settings(BaseSettings):
    """
    Application configuration with environment variable support.

    All settings can be overridden via environment variables with MARITIME_ prefix.
    """

    # Anthropic API Configuration
    anthropic_api_key: str = Field(
        ...,
        description="Anthropic API key for Claude Computer Use"
    )

    # Model Configuration
    model_name: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Claude model to use for agents"
    )
    max_tokens: int = Field(
        default=8000,
        description="Maximum tokens per API call"
    )
    temperature: float = Field(
        default=0.1,
        description="Model temperature for consistency"
    )

    # PostgreSQL Database Configuration
    postgres_host: str = Field(
        default="localhost",
        description="PostgreSQL host"
    )
    postgres_port: int = Field(
        default=5432,
        description="PostgreSQL port"
    )
    postgres_db: str = Field(
        default="maritime_intelligence",
        description="PostgreSQL database name"
    )
    postgres_user: str = Field(
        default="postgres",
        description="PostgreSQL username"
    )
    postgres_password: str = Field(
        ...,
        description="PostgreSQL password"
    )

    # Workflow Configuration
    max_retries: int = Field(
        default=3,
        description="Maximum retry attempts for failed operations"
    )
    parallel_sources: int = Field(
        default=7,
        description="Number of source scrapers to run in parallel"
    )
    parallel_searches: int = Field(
        default=6,
        description="Number of category searches to run in parallel"
    )

    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    log_format: str = Field(
        default="json",
        description="Log format: json or console"
    )

    # Execution Configuration
    execution_timeout: int = Field(
        default=600,
        description="Maximum execution time in seconds"
    )
    checkpoint_enabled: bool = Field(
        default=True,
        description="Enable LangGraph checkpointing"
    )

    # Source Configuration
    target_articles_per_source: int = Field(
        default=3,
        description="Target number of articles per source"
    )
    date_range_days: int = Field(
        default=2,
        description="Number of days back to search for articles"
    )

    @validator("anthropic_api_key")
    def validate_api_key(cls, v):
        if not v or not v.startswith(("sk-", "claude-")):
            raise ValueError("Invalid Anthropic API key format")
        return v

    @validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    @validator("temperature")
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Temperature must be between 0.0 and 1.0")
        return v

    @property
    def postgres_url(self) -> str:
        """
        Construct PostgreSQL connection URL.

        Returns:
            SQLAlchemy connection string
        """
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def postgres_async_url(self) -> str:
        """
        Construct async PostgreSQL connection URL.

        Returns:
            Async SQLAlchemy connection string
        """
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    class Config:
        env_prefix = "MARITIME_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Source configurations
NEWS_SOURCES = [
    {
        "name": "The Loadstar",
        "homepage": "https://theloadstar.com/",
        "target_count": 3,
        "priority": "high"
    },
    {
        "name": "Container News",
        "homepage": "https://container-news.com/",
        "target_count": 3,
        "priority": "high"
    },
    {
        "name": "gCaptain",
        "homepage": "https://gcaptain.com/",
        "target_count": 3,
        "priority": "medium"
    },
    {
        "name": "Kuehne+Nagel",
        "homepage": "https://mykn.kuehne-nagel.com/news/",
        "target_count": 3,
        "priority": "medium"
    },
    {
        "name": "Maersk",
        "homepage": "https://maersk.com/news",
        "target_count": 3,
        "priority": "high"
    },
    {
        "name": "CMA CGM",
        "homepage": "https://www.cma-cgm.com/latest-news",
        "target_count": 3,
        "priority": "high"
    },
    {
        "name": "Port News",
        "homepage": "https://en.portnews.ru/news/",
        "target_count": 3,
        "priority": "medium"
    }
]

# Category search configurations for Phase 2
CATEGORY_SEARCHES = [
    {
        "name": "Port Closures",
        "query": "port closure OR terminal closed",
        "category": "operational issues",
        "target_count": 5
    },
    {
        "name": "Congestion",
        "query": "port congestion OR vessel delays",
        "category": "congestion",
        "target_count": 5
    },
    {
        "name": "Red Sea",
        "query": "(Red Sea OR Suez Canal) shipping",
        "category": "red sea",
        "target_count": 5
    },
    {
        "name": "Weather",
        "query": "(storm OR hurricane) port",
        "category": "weather-related",
        "target_count": 5
    },
    {
        "name": "Carrier Updates",
        "query": "site:maersk.com OR site:cma-cgm.com",
        "category": "shipping line announcements",
        "target_count": 5
    },
    {
        "name": "Geopolitical",
        "query": "vessel seized OR sanctions",
        "category": "geopolitical",
        "target_count": 5
    }
]


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.

    Returns:
        Settings instance with validated configuration
    """
    return Settings()