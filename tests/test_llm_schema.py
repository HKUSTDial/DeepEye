import sys
import tomllib
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from app.llm.schema import Message, ToolCall, Function


def test_message_model():
    message = Message(role="user", content="Hello, world!")
    assert message.role == "user"
    assert message.content == "Hello, world!"
    print(message.to_dict())
    
test_message_model()