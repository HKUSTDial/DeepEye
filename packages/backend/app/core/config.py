from typing import List, Literal, Union
from pathlib import Path
from pydantic import AnyHttpUrl, computed_field, PostgresDsn, RedisDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
import re

class Settings(BaseSettings):
    PROJECT_NAME: str = "DeepEye API"
    API_V1_STR: str = "/api"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[Union[str, AnyHttpUrl]] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # --- Internal Service Defaults (Not typically user-configurable) ---
    
    # Database (System)
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "change-me-postgres-password"
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
    DOCKER_CONTROL_MODE: Literal["local", "remote"] = "local"
    DOCKER_CONTROL_URL: str = "http://runtime-control:8010"
    DOCKER_CONTROL_API_KEY: str = "change-me-runtime-control-key"
    DOCKER_CONTROL_TIMEOUT_SECONDS: float = 30.0
    SANDBOX_HOST: str = "code-sandbox"
    SANDBOX_PORT: int = 8000
    SANDBOX_IMAGE: str = "deepeye-sandbox:latest"
    SANDBOX_DOCKERFILE: str = "docker/Dockerfile.sandbox"
    # Project root: /path/to/DeepEye_refact
    SANDBOX_BUILD_CONTEXT: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    SANDBOX_AUTO_BUILD: bool = True
    SANDBOX_NO_NEW_PRIVILEGES: bool = True
    SANDBOX_DROP_ALL_CAPABILITIES: bool = True
    SANDBOX_NETWORK_DISABLED: bool = False
    SANDBOX_INIT_PROCESS: bool = True
    SANDBOX_PIDS_LIMIT: int = 256
    SANDBOX_MEMORY_LIMIT: str | None = "2g"
    SANDBOX_MEMORY_SWAP_LIMIT: str | None = "2g"
    SANDBOX_CPU_LIMIT: float | None = 2.0
    SANDBOX_TMPFS_SIZE_MB: int = 256
    SANDBOX_EXEC_TIMEOUT_SECONDS: int = 300
    
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
    MINIO_ACCESS_KEY: str = "change-me-minio-access-key"
    MINIO_SECRET_KEY: str = "change-me-minio-secret-key"
    MINIO_SECURE: bool = False
    MINIO_SANDBOX_BUCKET: str = "deepeye-sandboxes"  # Auto-build image if not exists
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
    LLM_MAX_TOKENS: int = 8192  # max tokens for completion across agent and artifact generation
    STARTUP_WARMUP_ENABLED: bool = True
    STARTUP_WARMUP_STRICT: bool = True
    STARTUP_WARMUP_TIMEOUT_SECONDS: float = 15.0
    LANGGRAPH_CHECKPOINTER_AUTO_SETUP: bool = True
    SANDBOX_CLEANUP_ENABLED: bool = True
    CELERY_STARTUP_WARMUP_ENABLED: bool = True
    AGENT_DATASOURCE_SCHEMA_CACHE_TTL_SECONDS: int = 300
    AGENT_DATASOURCE_SCHEMA_CACHE_MAX_ENTRIES: int = 128
    PREVIEW_RUNTIME_CLEANUP_ENABLED: bool = True
    PREVIEW_RUNTIME_CLEANUP_INTERVAL_SECONDS: int = 5 * 60
    PREVIEW_RUNTIME_TTL_SECONDS: int = 60 * 60
    PREVIEW_RUNTIME_MAX_CONTAINERS: int = 8
    
    # Azure Speech TTS (optional, for data video narration)
    AZURE_SPEECH_KEY: str | None = None
    AZURE_SPEECH_REGION: str | None = None

    # Video workspace: config and TSX output dirs. Default: /workspace (Docker); locally use VIDEO_WORKSPACE_DIR or auto fallback.
    VIDEO_WORKSPACE_DIR: str | None = None
    # Report workspace: temp CSV and intermediate report artifacts.
    # Default: /workspace (Docker); locally fallback to .report_workspace.
    REPORT_WORKSPACE_DIR: str | None = None

    # Docker image used by VideoDeployService to spin up per-task video preview containers.
    VIDEO_PREVIEW_IMAGE: str = "deepeye-video-preview:latest"
    VIDEO_PREVIEW_DOCKERFILE: str = "docker/Dockerfile.video-preview"
    VIDEO_PREVIEW_AUTO_BUILD: bool = True

    # JWT Authentication
    JWT_SECRET_KEY: str = "change-me-jwt-secret-key-at-least-32-chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # Access token 有效期（分钟）
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7      # Refresh token 有效期（天）
    AUTH_LOGIN_MAX_ATTEMPTS: int = 8
    AUTH_LOGIN_WINDOW_SECONDS: int = 300
    ACCESS_TOKEN_COOKIE_NAME: str = "deepeye_access_token"
    REFRESH_TOKEN_COOKIE_NAME: str = "deepeye_refresh_token"
    AUTH_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    AUTH_COOKIE_SECURE: bool = False
    EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 24 * 60
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    REQUIRE_EMAIL_VERIFICATION: bool = False
    AUTH_FRONTEND_BASE_URL: str = "http://localhost:5173"
    AUTH_DEBUG_RETURN_ACTION_TOKEN: bool = False
    AUTH_SMTP_HOST: str | None = None
    AUTH_SMTP_PORT: int = 587
    AUTH_SMTP_USERNAME: str | None = None
    AUTH_SMTP_PASSWORD: str | None = None
    AUTH_SMTP_USE_TLS: bool = True
    AUTH_EMAIL_FROM: str | None = None
    # Escape hatch for local development only.
    ALLOW_INSECURE_DEFAULTS: bool = False
    # Backward-compatibility escape hatch for legacy SSE clients using `?token=`.
    ALLOW_QUERY_TOKEN_FOR_STREAM: bool = False
    
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @model_validator(mode="after")
    def validate_sensitive_settings(self):
        if self.ALLOW_INSECURE_DEFAULTS:
            return self

        def _looks_insecure(value: str, blocked_tokens: set[str]) -> bool:
            normalized = (value or "").strip().lower()
            if not normalized:
                return True
            if normalized in blocked_tokens:
                return True
            if "change-me" in normalized or "replace-with" in normalized:
                return True
            return False

        if _looks_insecure(
            self.POSTGRES_PASSWORD,
            {"postgres", "password", "123456", "postgres123"},
        ):
            raise ValueError(
                "Insecure POSTGRES_PASSWORD. Set a strong value in .env "
                "or use ALLOW_INSECURE_DEFAULTS=true for local development."
            )

        if _looks_insecure(
            self.MINIO_ACCESS_KEY,
            {"minioadmin", "admin", "minio"},
        ):
            raise ValueError(
                "Insecure MINIO_ACCESS_KEY. Set a strong value in .env "
                "or use ALLOW_INSECURE_DEFAULTS=true for local development."
            )

        if _looks_insecure(
            self.MINIO_SECRET_KEY,
            {"minioadmin", "password", "123456"},
        ):
            raise ValueError(
                "Insecure MINIO_SECRET_KEY. Set a strong value in .env "
                "or use ALLOW_INSECURE_DEFAULTS=true for local development."
            )

        jwt_secret = (self.JWT_SECRET_KEY or "").strip()
        if _looks_insecure(
            jwt_secret,
            {"your-secret-key-change-this-in-production", "secret", "jwt-secret"},
        ) or len(jwt_secret) < 32:
            raise ValueError(
                "Insecure JWT_SECRET_KEY. Use at least 32 random characters "
                "or set ALLOW_INSECURE_DEFAULTS=true for local development."
            )

        if self.AUTH_COOKIE_SAMESITE == "none" and not self.AUTH_COOKIE_SECURE:
            raise ValueError(
                "AUTH_COOKIE_SAMESITE=none requires AUTH_COOKIE_SECURE=true "
                "or set ALLOW_INSECURE_DEFAULTS=true for local development."
            )

        return self

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


def get_report_workspace_root() -> Path:
    """Return writable root path for report temporary artifacts."""
    if settings.REPORT_WORKSPACE_DIR:
        root = Path(settings.REPORT_WORKSPACE_DIR)
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
    root = Path.cwd() / ".report_workspace"
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_report_session_root(session_id: str | None) -> Path:
    """
    Return per-session report runtime root.
    - session_id is set: {root}/sessions/{session_id}/report_runtime
    - session_id is empty: {root}/report_runtime
    """
    root = get_report_workspace_root()
    normalized = normalize_session_id(session_id)
    if not normalized:
        runtime_root = root / "report_runtime"
    else:
        runtime_root = root / "sessions" / normalized / "report_runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)
    return runtime_root
