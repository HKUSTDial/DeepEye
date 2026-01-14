from typing import List, Union
from pydantic import AnyHttpUrl, computed_field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "DeepEye API"
    API_V1_STR: str = "/api"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[Union[str, AnyHttpUrl]] = ["*"]

    # --- Internal Service Defaults (Not typically user-configurable) ---
    
    # Database (System)
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "deepeye"

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        return str(PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB
        ))

    # Database (State/LangGraph)
    POSTGRES_STATE_DB: str = "deepeye_state"
    
    @computed_field
    @property
    def POSTGRES_STATE_URL(self) -> str:
        return str(PostgresDsn.build(
            scheme="postgresql", 
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_STATE_DB
        ))

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    @computed_field
    @property
    def REDIS_URL(self) -> str:
        return str(RedisDsn.build(
            scheme="redis",
            host=self.REDIS_HOST,
            port=self.REDIS_PORT,
            path=f"{self.REDIS_DB}"
        ))

    # Sandbox
    SANDBOX_TYPE: str = "docker"  # docker, e2b, daytona
    SANDBOX_HOST: str = "code-sandbox"
    SANDBOX_PORT: int = 8000
    SANDBOX_IMAGE: str = "deepeye-sandbox:latest"
    SANDBOX_DOCKERFILE: str = "docker/Dockerfile.sandbox"
    # Project root: /path/to/DeepEye_refact
    SANDBOX_BUILD_CONTEXT: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    SANDBOX_AUTO_BUILD: bool = True
    
    # Sandbox Lifecycle Management
    SANDBOX_IDLE_TIMEOUT: int = 30 * 60        # 30 minutes - stop container
    SANDBOX_CLEANUP_INTERVAL: int = 5 * 60      # 5 minutes - check interval
    SANDBOX_DESTROY_TIMEOUT: int = 6 * 60 * 60  # 6 hours - destroy container (preserve volume)
    
    # MinIO Configuration
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    MINIO_SANDBOX_BUCKET: str = "deepeye-sandboxes"  # Auto-build image if not exists
    MINIO_KB_BUCKET: str = "deepeye-knowledge"
    MINIO_DATA_BUCKET: str = "deepeye-data"
    
    @computed_field
    @property
    def SANDBOX_URL(self) -> str:
        return f"http://{self.SANDBOX_HOST}:{self.SANDBOX_PORT}"
    # --- User Configurable Settings ---
    
    # LLM Provider Configuration (Required)
    LLM_API_KEY: str
    LLM_BASE_URL: str
    LLM_MODEL: str
    LLM_TEMPERATURE: float = 0.7
    
    # JWT Authentication
    JWT_SECRET_KEY: str = "your-secret-key-change-this-in-production"  # ⚠️ 生产环境必须修改
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # Access token 有效期（分钟）
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7      # Refresh token 有效期（天）
    
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
