"""Regression tests for supervisor orchestration order."""

import os

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.services.agent_prompts import build_supervisor_prompt
from deepeye.agents.factory import AgentFactory
from deepeye.tools.base import tool


class ToolCallingFakeChatModel(GenericFakeChatModel):
    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        return self


@pytest.mark.anyio
async def test_supervisor_routes_workflow_requests_through_summary_step():
    calls: list[tuple[str, str]] = []

    @tool
    async def workflow_agent(goal: str) -> dict:
        """Plan and run the workflow for a user goal."""
        calls.append(("workflow_agent", goal))
        return {
            "status": "success",
            "next_action": "summarize_workflow_result",
            "run_status": "success",
            "artifacts": ["report"],
        }

    @tool
    async def summarize_workflow_result(question: str) -> str:
        """Summarize the latest workflow result."""
        calls.append(("summarize_workflow_result", question))
        return "The workflow summary is ready."

    model = ToolCallingFakeChatModel(
        messages=iter(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "workflow_agent",
                        "args": {"goal": "Analyze sales.csv and summarize the trend"},
                        "id": "call_workflow",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "summarize_workflow_result",
                        "args": {"question": "Analyze sales.csv and summarize the trend"},
                        "id": "call_summary",
                        "type": "tool_call",
                    }
                ],
                ),
                AIMessage(content="The workflow summary is ready."),
            ]
        ),
    )

    supervisor = AgentFactory(model).create_supervisor(
        [workflow_agent, summarize_workflow_result],
        system_prompt_template=build_supervisor_prompt(),
    )

    result = await supervisor.ainvoke(
        "Analyze sales.csv and summarize the trend",
        thread_id="session-1",
        config={"configurable": {"datasources_context": "No data sources selected."}},
    )

    assert calls == [
        ("workflow_agent", "Analyze sales.csv and summarize the trend"),
        ("summarize_workflow_result", "Analyze sales.csv and summarize the trend"),
    ]
    assert result["messages"][-1].content == "The workflow summary is ready."
