from __future__ import annotations
import os
from typing import List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from app.core.config import settings

class Message:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

class LLMResponse:
    def __init__(self, content: str):
        self.content = content

class LLMClient:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url

    def generate(
        self, 
        messages: List[Message], 
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        resolved_model = (
            model
            or settings.LLM_MODEL
            or os.getenv("DEEPEYE_LLM_MODEL")
            or os.getenv("LLM_MODEL")
            or ""
        ).strip()
        if not resolved_model:
            raise ValueError("LLM model is required for dashboard generation")

        chat = ChatOpenAI(
            openai_api_key=self.api_key,
            openai_api_base=self.base_url,
            model_name=resolved_model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        langchain_messages = []
        for m in messages:
            if m.role == "user":
                langchain_messages.append(HumanMessage(content=m.content))
            elif m.role == "system":
                langchain_messages.append(SystemMessage(content=m.content))
            elif m.role == "assistant":
                langchain_messages.append(AIMessage(content=m.content))
            else:
                langchain_messages.append(HumanMessage(content=m.content))
        
        response = chat.invoke(langchain_messages)
        return LLMResponse(content=str(response.content))
