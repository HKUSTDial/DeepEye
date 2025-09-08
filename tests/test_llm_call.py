import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from app.llm import LLM
import asyncio

def test_llm_call():
    llm = LLM(config_name="default")
    response = asyncio.run(llm.ask(messages=[{"role": "user", "content": "Hello, world!"}]))
    assert response is not None
    print(response)

def test_llm_tool_call():
    llm = LLM(config_name="default")
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_time",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "timezone": {
                            "type": "string",
                            "description": "The timezone to get the time for",
                            "enum": ["UTC", "GMT", "CET", "EST", "PST", "Asia/Shanghai", "Asia/Tokyo"]
                        }
                    },
                    "required": ["timezone"],
                    "additionalProperties": False
                }
            }
        }
    ]
    response = asyncio.run(llm.ask(messages=[{"role": "user", "content": "What is the current time (in UTC)?"}], tools=tools, tool_choice="auto"))
    assert response is not None
    print(response)

test_llm_tool_call()