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
from app.tasks.callbacks import MessageCollector
from app.tools.workflow_tools import _extract_final_answer
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


@pytest.mark.anyio
async def test_supervisor_replies_directly_when_workflow_agent_returns_final_answer():
    calls: list[tuple[str, str]] = []

    @tool
    async def workflow_agent(goal: str) -> dict:
        """Plan and run the workflow for a user goal."""
        calls.append(("workflow_agent", goal))
        return {
            "status": "success",
            "next_action": "reply_directly",
            "run_status": "success",
            "final_answer": "Final grounded workflow answer.",
        }

    @tool
    async def summarize_workflow_result(question: str) -> str:
        """Summarize the latest workflow result."""
        calls.append(("summarize_workflow_result", question))
        return "This should not be used."

    model = ToolCallingFakeChatModel(
        messages=iter(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "workflow_agent",
                            "args": {"goal": "Find the highest revenue city"},
                            "id": "call_workflow",
                            "type": "tool_call",
                        }
                    ],
                ),
                AIMessage(content="Final grounded workflow answer."),
            ]
        ),
    )

    supervisor = AgentFactory(model).create_supervisor(
        [workflow_agent, summarize_workflow_result],
        system_prompt_template=build_supervisor_prompt(),
    )

    result = await supervisor.ainvoke(
        "Find the highest revenue city",
        thread_id="session-1",
        config={"configurable": {"datasources_context": "No data sources selected."}},
    )

    assert calls == [("workflow_agent", "Find the highest revenue city")]
    assert result["messages"][-1].content == "Final grounded workflow answer."


def test_message_collector_prefers_summary_tool_output() -> None:
    collector = MessageCollector()
    collector.add_token("supervisor", "I will analyze this for you. ")
    collector.start_tool("supervisor", "workflow_agent", "{}")
    collector.end_tool("supervisor", '{"status":"success"}')
    collector.start_tool("supervisor", "summarize_workflow_result", '{"question":"Analyze"}')
    collector.end_tool("supervisor", "Final concise answer.")
    collector.add_token("supervisor", "I will analyze this for you. Final concise answer.")

    message = collector.build()

    assert message.content == "Final concise answer."


def test_extract_final_answer_prefers_workflow_answer_output() -> None:
    workspace_state = {
        "run": {
            "status": "success",
            "result": {
                "outputs": {
                    "join": {"dataset_ref": {"kind": "dataset_ref", "path": "/workspace/a.jsonl", "format": "jsonl"}},
                    "answer": {"answer": "The final grounded answer."},
                }
            },
        }
    }

    assert _extract_final_answer(workspace_state) == "The final grounded answer."


def test_supervisor_does_not_inject_plan_tools() -> None:
    model = ToolCallingFakeChatModel(messages=iter([AIMessage(content="Done.")]))

    @tool
    async def workflow_agent(goal: str) -> dict:
        """Plan and run the workflow for a user goal."""
        return {"status": "success", "goal": goal}

    supervisor = AgentFactory(model).create_supervisor(
        [workflow_agent],
        system_prompt_template=build_supervisor_prompt(),
    )

    assert [tool.name for tool in supervisor.tools] == ["workflow_agent"]
