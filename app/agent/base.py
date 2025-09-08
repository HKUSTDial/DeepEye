from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Optional
from enum import Enum

from app.llm import Message, Memory, LLM, RoleType
from app.logger import logger
from pydantic import BaseModel, Field, model_validator, ConfigDict


class AgentState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    FINISHED = "finished"
    ERROR = "error"


class BaseAgent(ABC, BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    name: str = Field(..., description="The unique name of the agent")
    description: Optional[str] = Field(default=None, description="The description of the agent")
    
    system_prompt: Optional[str] = Field(default=None, description="The system prompt of the agent")
    next_step_prompt: Optional[str] = Field(default=None, description="The next step prompt of the agent")
    
    llm: LLM = Field(default_factory=LLM, description="The llm of the agent")
    memory: Memory = Field(default_factory=Memory, description="The memory of the agent")
    state: AgentState = Field(default=AgentState.IDLE, description="The state of the agent")
    
    max_steps: int = Field(default=30, description="The maximum number of steps the agent can take")
    current_step: int = Field(default=0, description="The current step of the agent")
    
    @model_validator(mode="after")
    def _initialize_agent(self) -> "BaseAgent":
        if self.llm is None:
            self.llm = LLM(config_name=self.name)
        if self.memory is None:
            self.memory = Memory()
        return self
    
    def update_memory(self,
                      role: RoleType,
                      content: Optional[str] = None,
                      **kwargs) -> None:
        message_map = {
            RoleType.SYSTEM: Message.system_message,
            RoleType.USER: Message.user_message,
            RoleType.ASSISTANT: Message.assistant_message,
            RoleType.TOOL: Message.tool_message,
        }
        message = message_map[role](content, **kwargs)
        self.memory.add_message(message)

    @asynccontextmanager
    async def state_context(self, new_state: AgentState) -> None:
        if not isinstance(new_state, AgentState):
            raise ValueError(f"Invalid state: {new_state}")
        
        old_state = self.state
        self.state = new_state
        try:
            yield
        except Exception as e:
            self.state = AgentState.ERROR
            raise e
        finally:
            self.state = old_state
    
    @abstractmethod
    async def step(self) -> None:
        pass
    
    async def run(self, request: Optional[str] = None) -> None:
        if self.state != AgentState.IDLE:
            raise RuntimeError(f"Agent is not in idle state: {self.state}")
        
        if request:
            self.update_memory(RoleType.USER, request)
        
        async with self.state_context(AgentState.RUNNING):
            while self.current_step < self.max_steps and self.state != AgentState.FINISHED:
                self.current_step += 1
                logger.info(f"🔄 Agent {self.name} is running step {self.current_step}")
                await self.step()
            
        self.current_step = 0
        
        