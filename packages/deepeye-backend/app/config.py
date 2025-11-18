"""
Application configuration using Pydantic Settings.
Loads configuration from environment variables.
"""
from typing import List

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "DeepEye API"
    VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    # DATABASE_URL can be set directly, or auto-constructed from POSTGRES_* variables
    DATABASE_URL: str = ""
    
    # PostgreSQL connection components (optional, for auto-constructing DATABASE_URL)
    POSTGRES_DB: str = "deepeye"
    POSTGRES_USER: str = "deepeye"
    POSTGRES_PASSWORD: str = "deepeye"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # CORS
    # Store as string to avoid JSON parsing issues, convert to list via property
    cors_origins_str: str = Field(default="", alias="BACKEND_CORS_ORIGINS")

    @property
    def BACKEND_CORS_ORIGINS(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        if not self.cors_origins_str:
            return []
        return [origin.strip() for origin in self.cors_origins_str.split(",") if origin.strip()]

    @model_validator(mode="after")
    def build_database_url(self) -> "Settings":
        """Auto-construct DATABASE_URL from POSTGRES_* variables if not set."""
        if not self.DATABASE_URL:
            # Build DATABASE_URL from POSTGRES_* variables
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        return self

    # Email
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_TLS: bool = True

    # Logging
    LOG_LEVEL: str = "INFO"

    # LLM (for deepeye-core)
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4"

    # Storage (Minio)
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "deepeye"
    MINIO_SECURE: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Global settings instance
settings = Settings()


