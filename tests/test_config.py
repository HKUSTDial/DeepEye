import sys
import tomllib
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from app.config.config import Config


def test_local_config_file_exists():
    assert (PROJECT_ROOT / "config" / "config.toml").exists()
    
def _load_local_config():
    with open(PROJECT_ROOT / "config" / "config.toml", "rb") as f:
        return tomllib.load(f)


def test_default_llm_config():
    config = Config()
    local_config = _load_local_config()
    assert config.app_config is not None
    assert config.llm_config is not None
    assert config.llm_config["default"] is not None
    assert config.llm_config["default"].model == local_config["llm"]["model"]
    assert config.llm_config["default"].base_url == local_config["llm"]["base_url"]
    assert config.llm_config["default"].api_key == local_config["llm"]["api_key"]
    assert config.llm_config["default"].max_tokens == local_config["llm"].get("max_tokens", 4096)
    assert config.llm_config["default"].temperature == local_config["llm"].get("temperature", 0.7)
    assert config.llm_config["default"].api_type == local_config["llm"].get("api_type", "openai")
    assert config.llm_config["default"].api_version == local_config["llm"].get("api_version", None)
