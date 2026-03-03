from typing import List, Union
from pathlib import Path
from pydantic import AnyHttpUrl, computed_field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
import re

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

    # Dashboard deployment runtime
    DASHBOARD_IMAGE: str = "deepeye-dashboard:latest"
    DASHBOARD_DOCKERFILE: str = "docker/Dockerfile.dashboard"
    DASHBOARD_AUTO_BUILD: bool = True
    
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
    LLM_MAX_TOKENS: int = 32000  # max tokens for completion (video TSX, config, etc.)
    
    # Azure Speech TTS (optional, for data video narration)
    AZURE_SPEECH_KEY: str | None = None
    AZURE_SPEECH_REGION: str | None = None

    # Video workspace: config and TSX output dirs. Default: /workspace (Docker); locally use VIDEO_WORKSPACE_DIR or auto fallback.
    VIDEO_WORKSPACE_DIR: str | None = None

    # Docker image used by VideoDeployService to spin up per-task video preview containers.
    VIDEO_PREVIEW_IMAGE: str = "deepeye-video-preview:latest"

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

_SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


def get_video_workspace_root() -> Path:
    """Return base path for video_configs and video_components. Writable; works in Docker and locally."""
    if settings.VIDEO_WORKSPACE_DIR:
        root = Path(settings.VIDEO_WORKSPACE_DIR)
        root.mkdir(parents=True, exist_ok=True)
        return root
    p = Path("/workspace")
    if p.exists():
        try:
            (p / ".write_test").write_text("")
            (p / ".write_test").unlink(missing_ok=True)
            return p
        except OSError:
            pass
    root = Path.cwd() / ".video_workspace"
    root.mkdir(parents=True, exist_ok=True)
    return root


def normalize_session_id(session_id: str | None) -> str | None:
    """Normalize and validate session_id for filesystem path usage."""
    if session_id is None:
        return None
    value = session_id.strip()
    if not value:
        return None
    if not _SESSION_ID_PATTERN.fullmatch(value):
        raise ValueError("Invalid session_id format")
    return value


def get_video_session_root(session_id: str | None) -> Path:
    """
    Return per-session workspace root for video artifacts.
    - session_id is set: /workspace/sessions/{session_id}
    - session_id is empty: legacy shared /workspace
    """
    root = get_video_workspace_root()
    normalized = normalize_session_id(session_id)
    if not normalized:
        return root
    session_root = root / "sessions" / normalized
    session_root.mkdir(parents=True, exist_ok=True)
    return session_root
