import json
import tomllib
import threading
from typing import Dict, List, Optional, Literal, Any
from pathlib import Path
from pydantic import BaseModel, Field


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


PROJECT_ROOT = get_project_root()
WORKSPACE_ROOT = PROJECT_ROOT / "workspace"


class LLMConfig(BaseModel):
    model: str = Field(..., description="The model name")
    base_url: str = Field(..., description="The base url of the model service")
    api_key: str = Field(..., description="The api key of the model service")
    max_tokens: int = Field(default=4096, description="The maximum number of tokens to generate per request")
    temperature: float = Field(default=0.7, description="The temperature of the model")
    api_type: Literal["openai", "azure"] = Field(default="openai", description="The type of the api")
    api_version: Optional[str] = Field(default=None, description="The version of the Azure API")


class SQLiteDatabaseConfig(BaseModel):
    path: Optional[str] = Field(default=None, description="The path of the sqlite database")


class AppConfig(BaseModel):
    llm: Dict[str, LLMConfig] = Field(default_factory=dict, description="The llm config")
    sqlite_database: SQLiteDatabaseConfig = Field(default_factory=SQLiteDatabaseConfig, description="The sqlite database config")


class Config:
    _app_config: AppConfig = None
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self._initialize_config()

    @staticmethod
    def _get_config_path():
        config_path = PROJECT_ROOT / "config" / "config.toml"
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found at {config_path}")
        return config_path
    
    @staticmethod
    def _load_config():
        with open(Config._get_config_path(), "rb") as f:
            return tomllib.load(f)

    def _initialize_config(self):
        config = Config._load_config()
        
        # llm config
        default_llm_config = config.get("llm", {})
        default_llm_settings = {
            "model": default_llm_config.get("model"),
            "base_url": default_llm_config.get("base_url"),
            "api_key": default_llm_config.get("api_key"),
            "max_tokens": default_llm_config.get("max_tokens", 4096),
            "temperature": default_llm_config.get("temperature", 0.7),
            "api_type": default_llm_config.get("api_type", "openai"),
            "api_version": default_llm_config.get("api_version", None),
        }
        specific_llms = {
            k: v for k, v in config.get("llm", {}).items() if isinstance(v, dict)
        }
        
        # sqlite database config
        sqlite_database_config = config.get("sqlite_database", {})
        sqlite_database_settings = {
            "path": sqlite_database_config.get("path", None),
        }
        
        self._app_config = AppConfig(
            llm={
                "default": LLMConfig(**default_llm_settings),
                **{
                    f"{k}": LLMConfig(**v) for k, v in specific_llms.items()
                },
            },
            sqlite_database=SQLiteDatabaseConfig(**sqlite_database_settings),
        )

    @property
    def app_config(self):
        return self._app_config
    
    @property
    def llm_config(self):
        return self._app_config.llm
    
    @property
    def sqlite_database_config(self):
        return self._app_config.sqlite_database

# global config instance
config = Config()