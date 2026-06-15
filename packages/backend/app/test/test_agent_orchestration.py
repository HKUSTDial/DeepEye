"""Regression tests for supervisor orchestration order."""

import json
import os
from collections.abc import Iterator
from typing import Any

import pytest
from langchain_core.callbacks import AsyncCallbackManagerForLLMRun, CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.agent.prompts import build_supervisor_prompt
from app.workflow.services.workspace_state import extract_final_answer
from app.tasks.callbacks import MessageCollector, _workflow_tool_trace_summary
from app.tools.workflow_tools import (
    _new_repair_state,
    _normalize_workflow_payload_shape,
    _normalize_workflow_run_result,
    _require_reuse_after_failure,
    create_workflow_and_run_tool,
    create_read_workflow_tool,
    create_update_workflow_tool,
    create_design_workflow_tool,
    create_summarize_workflow_result_tool,
)
from deepeye.agents.factory import AgentFactory
from deepeye.tools.base import tool


class ToolCallingFakeChatModel(BaseChatModel):
    messages: Iterator[AIMessage | str]

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        del messages, stop, run_manager, kwargs
        message = next(self.messages)
        generated = AIMessage(content=message) if isinstance(message, str) else message
        return ChatResult(generations=[ChatGeneration(message=generated)])

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return self._generate(messages, stop=stop, run_manager=None, **kwargs)

    @property
    def _llm_type(self) -> str:
        return "tool-calling-fake-chat-model"


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


@pytest.mark.anyio
async def test_supervisor_short_circuits_after_workflow_agent_final_answer_tool_message():
    calls: list[tuple[str, str]] = []

    @tool
    async def workflow_agent(goal: str) -> dict:
        """Plan and run the workflow for a user goal."""
        calls.append(("workflow_agent", goal))
        return {
            "status": "failed",
            "next_action": "reply_directly",
            "final_answer": "工作流规划未收敛，请缩小问题范围后重试。",
        }

    model = ToolCallingFakeChatModel(
        messages=iter(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "workflow_agent",
                            "args": {"goal": "分析附加数据并回答问题"},
                            "id": "call_workflow",
                            "type": "tool_call",
                        }
                    ],
                ),
            ]
        ),
    )

    supervisor = AgentFactory(model).create_supervisor(
        [workflow_agent],
        system_prompt_template=build_supervisor_prompt(),
    )

    result = await supervisor.ainvoke(
        "分析附加数据并回答问题",
        thread_id="session-1",
        config={"configurable": {"datasources_context": "No data sources selected."}},
    )

    assert calls == [("workflow_agent", "分析附加数据并回答问题")]
    assert result["messages"][-1].content == "工作流规划未收敛，请缩小问题范围后重试。"


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


@pytest.mark.anyio
async def test_summary_tool_marks_nested_model_call_as_sub_agent(monkeypatch) -> None:
    class _FakeDb:
        def close(self) -> None:
            return None

    class _CapturingModel:
        def __init__(self) -> None:
            self.config = None

        async def ainvoke(self, messages, config=None):
            self.config = config
            assert len(messages) == 2
            return AIMessage(content="Summary ready.")

    monkeypatch.setattr("app.tools.workflow_tools.SessionLocal", lambda: _FakeDb())
    monkeypatch.setattr(
        "app.tools.workflow_tools.build_workspace_state",
        lambda db, session_id: {
            "session_id": session_id,
            "turn": None,
            "draft": None,
            "run": type(
                "Run",
                (),
                {
                    "id": "run-1",
                    "status": "success",
                    "error": None,
                    "result": {"outputs": {"dash": {"dashboard_url": "/dashboards/demo/"}}},
                },
            )(),
            "artifacts": [],
        },
    )

    model = _CapturingModel()
    summarize_tool = create_summarize_workflow_result_tool(model, "session-1")

    result = await summarize_tool.ainvoke({"question": "Summarize the dashboard"})

    assert result == "Summary ready."
    assert model.config == {"tags": ["sub_agent"]}


def test_message_collector_uses_fallback_content_on_failure() -> None:
    collector = MessageCollector()
    collector.start_tool("supervisor", "workflow_agent", "{}")
    collector.fail_tool("supervisor", "Recursion limit hit.")

    message = collector.build(fallback_content="工作流规划未收敛，系统已停止自动重试。")

    assert message.content == "工作流规划未收敛，系统已停止自动重试。"
    assert message.steps[0].status == "error"
    assert message.steps[0].output == "Recursion limit hit."


def test_message_collector_prefers_workflow_agent_final_answer() -> None:
    collector = MessageCollector()
    collector.add_token("supervisor", "我来帮您分析。")
    collector.start_tool("supervisor", "workflow_agent", "{}")
    collector.end_tool(
        "supervisor",
        '{"status":"failed","next_action":"reply_directly","final_answer":"工作流规划未收敛，请补充更明确的目标后重试。"}',
    )

    message = collector.build()

    assert message.content == "工作流规划未收敛，请补充更明确的目标后重试。"


def test_workflow_tool_trace_summary_compacts_run_metadata() -> None:
    summary = _workflow_tool_trace_summary(
        stage="end",
        source="workflow_agent",
        tool_name="create_workflow_and_run",
        session_id="session-1",
        turn_id="turn-1",
        payload={
            "status": "success",
            "draft_id": "draft-1",
            "run": {
                "status": "failed",
                "run_id": "run-1",
                "validation_errors": [{"code": "missing_param"}],
                "details": [{"loc": ["root", "nodes", 0]}],
                "artifacts": [{"kind": "report"}],
            },
        },
    )

    assert summary["status"] == "failed"
    assert summary["draft_id"] == "draft-1"
    assert summary["run_id"] == "run-1"
    assert summary["validation_error_count"] == 1
    assert summary["details_count"] == 1
    assert summary["artifact_kinds"] == ["report"]


def test_normalize_workflow_run_result_marks_repairable_definition_failures() -> None:
    normalized = _normalize_workflow_run_result(
        {
            "status": "failed",
            "details": [
                {"loc": ["root", "nodes", 0, "id"], "msg": "Field required"},
                {"loc": ["root", "edges"], "msg": "Invalid value"},
            ],
        },
        draft_id="draft-1",
    )

    assert normalized["status"] == "failed"
    assert normalized["repairable"] is True
    assert normalized["error_type"] == "workflow_definition_invalid"
    assert normalized["draft_id"] == "draft-1"
    assert len(normalized["issues"]) == 2


def test_normalize_workflow_run_result_marks_python_schema_failures_repairable() -> None:
    normalized = _normalize_workflow_run_result(
        {
            "status": "failed",
            "error": (
                "Workflow execution failed at node join_data (python.code): KeyError: city\n"
                'INPUT_PREVIEW (first 10 lines): {"dataset_ref":[{"columns":["city","total_revenue","total_orders"]}]}'
            ),
            "details": [
                {
                    "node_id": "join_data",
                    "node_type": "python.code",
                    "message": "KeyError: city",
                }
            ],
        },
        draft_id="draft-1",
    )

    assert normalized["status"] == "failed"
    assert normalized["repairable"] is True
    assert normalized["error_type"] == "workflow_python_schema_invalid"
    assert "total_revenue" in normalized["issues"][-1]


def test_normalize_workflow_run_result_marks_python_dataset_ref_contract_failures_repairable() -> None:
    normalized = _normalize_workflow_run_result(
        {
            "status": "failed",
            "error": (
                "Workflow execution failed at node analyze_campaign_data (python.code): "
                "AttributeError: 'list' object has no attribute 'get'\n"
                'INPUT_PREVIEW (first 10 lines): {"dataset_ref":[{"path":"/workspace/data/campaign.csv","preview_rows":[{"city":"Shanghai"}]}]}'
            ),
            "details": [
                {
                    "node_id": "analyze_campaign_data",
                    "node_type": "python.code",
                    "message": "AttributeError: 'list' object has no attribute 'get'",
                }
            ],
        },
        draft_id="draft-1",
    )

    assert normalized["status"] == "failed"
    assert normalized["repairable"] is True
    assert normalized["error_type"] == "workflow_python_contract_invalid"
    assert "load_dataset_ref(ref)" in normalized["issues"][1]


def test_normalize_workflow_run_result_marks_missing_artifact_dataset_ref_repairable() -> None:
    workflow = {
        "root": {
            "nodes": {
                "read": {"id": "read", "type": "datasource.read", "params": {"datasource_id": "ds-1"}},
                "join_and_aggregate": {"id": "join_and_aggregate", "type": "python.code", "params": {"code": "print('ok')"}},
                "generate_report": {"id": "generate_report", "type": "report.generate", "params": {"query": "Build report"}},
            },
            "edges": {
                "e1": {
                    "id": "e1",
                    "source": {"node_id": "read", "port_id": "dataset_ref"},
                    "target": {"node_id": "join_and_aggregate", "port_id": "dataset_ref"},
                }
            },
        }
    }

    normalized = _normalize_workflow_run_result(
        {
            "status": "failed",
            "error": "Workflow execution failed at node generate_report (report.generate): dataset_ref input is required",
            "details": [
                {
                    "node_id": "generate_report",
                    "node_type": "report.generate",
                    "message": "dataset_ref input is required",
                }
            ],
        },
        draft_id="draft-1",
        workflow_definition=workflow,
    )

    assert normalized["status"] == "failed"
    assert normalized["repairable"] is True
    assert normalized["error_type"] == "workflow_artifact_input_missing"
    assert normalized["issues"] == ["Connect join_and_aggregate.dataset_ref -> generate_report.dataset_ref."]


def test_normalize_workflow_run_result_marks_missing_artifact_dataset_output_repairable() -> None:
    workflow = {
        "root": {
            "nodes": {
                "join_and_aggregate": {"id": "join_and_aggregate", "type": "python.code", "params": {"code": "print('done')"}},
                "generate_report": {"id": "generate_report", "type": "report.generate", "params": {"query": "Build report"}},
            },
            "edges": {
                "e1": {
                    "id": "e1",
                    "source": {"node_id": "join_and_aggregate", "port_id": "dataset_ref"},
                    "target": {"node_id": "generate_report", "port_id": "dataset_ref"},
                }
            },
        }
    }

    normalized = _normalize_workflow_run_result(
        {
            "status": "failed",
            "error": "Workflow execution failed at node generate_report (report.generate): dataset_ref input is required",
            "details": [
                {
                    "node_id": "generate_report",
                    "node_type": "report.generate",
                    "message": "dataset_ref input is required",
                }
            ],
        },
        draft_id="draft-1",
        workflow_definition=workflow,
    )

    assert normalized["status"] == "failed"
    assert normalized["repairable"] is True
    assert normalized["error_type"] == "workflow_dataset_output_missing"
    assert "already has incoming dataset_ref edge" in normalized["issues"][0]
    assert "Keep `join_and_aggregate` if it performs a required transform" in normalized["issues"][0]
    assert "`emit_dataframe(df)`" in normalized["issues"][0]


def test_normalize_workflow_run_result_marks_missing_transform_dataset_ref_repairable() -> None:
    workflow = {
        "root": {
            "nodes": {
                "read": {"id": "read", "type": "datasource.read", "params": {"datasource_id": "ds-1"}},
                "join_and_aggregate": {"id": "join_and_aggregate", "type": "python.code", "params": {"code": "print('ok')"}},
                "sort_by_revenue": {"id": "sort_by_revenue", "type": "rows.sort", "params": {"by": "total_revenue"}},
                "generate_report": {"id": "generate_report", "type": "report.generate", "params": {"query": "Build report"}},
            },
            "edges": {
                "e1": {
                    "id": "e1",
                    "source": {"node_id": "read", "port_id": "dataset_ref"},
                    "target": {"node_id": "join_and_aggregate", "port_id": "dataset_ref"},
                }
            },
        }
    }

    normalized = _normalize_workflow_run_result(
        {
            "status": "failed",
            "error": "Workflow execution failed at node sort_by_revenue (rows.sort): Required input missing: sort_by_revenue.dataset_ref",
            "details": [
                {
                    "node_id": "sort_by_revenue",
                    "node_type": "rows.sort",
                    "message": "Required input missing: sort_by_revenue.dataset_ref",
                }
            ],
        },
        draft_id="draft-1",
        workflow_definition=workflow,
    )

    assert normalized["status"] == "failed"
    assert normalized["repairable"] is True
    assert normalized["error_type"] == "workflow_dataset_input_missing"
    assert normalized["issues"] == ["Connect join_and_aggregate.dataset_ref -> sort_by_revenue.dataset_ref."]


def test_normalize_workflow_run_result_marks_invalid_sql_as_repairable() -> None:
    normalized = _normalize_workflow_run_result(
        {
            "status": "failed",
            "error": "Workflow execution failed at node query_sales (sql.execute): column city does not exist",
            "details": [
                {
                    "node_id": "query_sales",
                    "node_type": "sql.execute",
                    "message": '(psycopg2.errors.UndefinedColumn) column "city" does not exist',
                }
            ],
        },
        draft_id="draft-1",
    )

    assert normalized["status"] == "failed"
    assert normalized["repairable"] is True
    assert normalized["error_type"] == "workflow_sql_query_invalid"
    assert "Do not reference file-only columns inside SQL." in normalized["issues"][1]


def test_normalize_workflow_run_result_marks_invalid_node_inputs_wiring_repairable() -> None:
    normalized = _normalize_workflow_run_result(
        {
            "status": "failed",
            "details": [
                {
                    "type": "model_type",
                    "loc": ["nodes", "join_data", "inputs", "dataset_ref"],
                    "msg": "Input should be a valid dictionary or instance of Port",
                }
            ],
        },
        draft_id="draft-1",
    )

    assert normalized["status"] == "failed"
    assert normalized["repairable"] is True
    assert normalized["error_type"] == "workflow_wiring_invalid"
    assert "connect upstream nodes through `root.edges` only" in normalized["issues"][0]


def test_repair_state_requires_reusing_existing_draft_after_failure() -> None:
    state = _new_repair_state()
    state["repair_failures"] = 1
    state["active_draft_id"] = "draft-123"

    failure = _require_reuse_after_failure(state, draft_id=None)

    assert failure is not None
    assert failure["status"] == "failed"
    assert failure["repairable"] is True
    assert failure["error_type"] == "draft_reuse_required"
    assert failure["draft_id"] == "draft-123"


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

    assert extract_final_answer(workspace_state) == "The final grounded answer."


def test_normalize_workflow_payload_shape_converts_list_nodes_and_edges() -> None:
    workflow = {
        "id": "wf-1",
        "root": {
            "nodes": [
                {"id": "read_file", "type": "datasource.read", "params": {"datasource_id": "ds-1"}},
                {"id": "answer", "type": "llm.answer", "params": {"question": "Q"}},
            ],
            "edges": [
                {
                    "id": "edge-1",
                    "source": {"node_id": "read_file", "port_id": "dataset_ref"},
                    "target": {"node_id": "answer", "port_id": "dataset_ref"},
                }
            ],
        },
    }

    normalized = _normalize_workflow_payload_shape(workflow)

    assert isinstance(normalized["root"]["nodes"], dict)
    assert isinstance(normalized["root"]["edges"], dict)
    assert set(normalized["root"]["nodes"].keys()) == {"read_file", "answer"}
    assert set(normalized["root"]["edges"].keys()) == {"edge-1"}


def test_normalize_workflow_payload_shape_parses_stringified_nodes_and_edges() -> None:
    workflow = {
        "id": "wf-1",
        "root": {
            "nodes": json.dumps(
                {
                    "read_file": {"id": "read_file", "type": "datasource.read", "params": {"datasource_id": "ds-1"}},
                    "answer": {"id": "answer", "type": "llm.answer", "params": {"question": "Q"}},
                }
            ),
            "edges": json.dumps(
                {
                    "edge-1": {
                        "id": "edge-1",
                        "source": {"node_id": "read_file", "port_id": "dataset_ref"},
                        "target": {"node_id": "answer", "port_id": "dataset_ref"},
                    }
                }
            ),
        },
    }

    normalized = _normalize_workflow_payload_shape(workflow)

    assert isinstance(normalized["root"]["nodes"], dict)
    assert isinstance(normalized["root"]["edges"], dict)
    assert set(normalized["root"]["nodes"].keys()) == {"read_file", "answer"}
    assert set(normalized["root"]["edges"].keys()) == {"edge-1"}


def test_normalize_workflow_payload_shape_parses_stringified_workflow_root() -> None:
    workflow = json.dumps(
        {
            "id": "wf-1",
            "root": {
                "nodes": [
                    {"id": "read_file", "type": "datasource.read", "params": {"datasource_id": "ds-1"}},
                    {"id": "answer", "type": "llm.answer", "params": {"question": "Q"}},
                ],
                "edges": [
                    {
                        "id": "edge-1",
                        "source": {"node_id": "read_file", "port_id": "dataset_ref"},
                        "target": {"node_id": "answer", "port_id": "dataset_ref"},
                    }
                ],
            },
        }
    )

    normalized = _normalize_workflow_payload_shape(workflow)

    assert isinstance(normalized, dict)
    assert isinstance(normalized["root"]["nodes"], dict)
    assert isinstance(normalized["root"]["edges"], dict)
    assert set(normalized["root"]["nodes"].keys()) == {"read_file", "answer"}
    assert set(normalized["root"]["edges"].keys()) == {"edge-1"}


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


def test_workflow_tools_expose_planning_notes_field() -> None:
    create_tool = create_workflow_and_run_tool("session-1")
    update_tool = create_update_workflow_tool("session-1", "user-1")

    create_schema = create_tool.args_schema.model_json_schema()
    update_schema = update_tool.args_schema.model_json_schema()

    assert "planning_notes" in create_schema["properties"]
    assert "planning_notes" in update_schema["properties"]


def test_workflow_tool_optional_strings_use_plain_string_schema() -> None:
    tools = [
        create_workflow_and_run_tool("session-1"),
        create_update_workflow_tool("session-1", "user-1"),
        create_read_workflow_tool("session-1"),
    ]

    for tool_obj in tools:
        schema = tool_obj.args_schema.model_json_schema()
        for field_name in ("draft_id", "name", "file_path", "planning_notes"):
            field_schema = schema["properties"].get(field_name)
            if field_schema is not None:
                assert field_schema.get("type") == "string"
                assert "anyOf" not in field_schema


@pytest.mark.anyio
async def test_workflow_agent_uses_compact_toolset(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakeDb:
        def close(self) -> None:
            return None

    class _FakeWorkflowAgent:
        def __init__(self, *, model, system_prompt, tools, max_steps, **kwargs):
            del model, system_prompt, kwargs
            captured["tool_names"] = [tool.name for tool in tools]
            captured["max_steps"] = max_steps

        async def ainvoke(self, goal: str, thread_id: str | None = None, config: dict | None = None):
            del goal, thread_id, config
            return {"messages": []}

    monkeypatch.setattr("app.tools.workflow_tools.SessionLocal", lambda: _FakeDb())
    monkeypatch.setattr(
        "app.tools.workflow_tools.get_workflow_session",
        lambda db, session_id: type("Session", (), {"user_id": "user-1"})(),
    )
    monkeypatch.setattr("app.tools.workflow_tools.WorkflowAgent", _FakeWorkflowAgent)
    monkeypatch.setattr(
        "app.workflow.services.agent_response.build_workspace_state",
        lambda db, session_id: {
            "session_id": session_id,
            "draft": type("Draft", (), {"id": "draft-1", "status": "ready", "version": 1, "source": "workflow_agent"})(),
            "run": type("Run", (), {"id": "run-1", "status": "success", "error": None, "result": {"outputs": {}}})(),
            "artifacts": [],
        },
    )

    workflow_tool = create_design_workflow_tool(
        model=ToolCallingFakeChatModel(messages=iter([AIMessage(content="Done.")])),
        session_id="session-1",
        system_prompt="test prompt",
        callbacks=[],
        turn_id=None,
    )

    result = await workflow_tool.ainvoke({"goal": "Analyze the attached data"})

    assert result["status"] == "success"
    assert captured["tool_names"] == [
        "create_workflow_and_run",
        "read_workflow",
        "update_workflow",
        "run_workflow",
    ]
    assert captured["max_steps"] == 24


@pytest.mark.anyio
async def test_workflow_agent_returns_terminal_failure_without_summary(monkeypatch) -> None:
    class _FakeDb:
        def close(self) -> None:
            return None

    class _FakeWorkflowAgent:
        def __init__(self, *, stop_condition=None, **kwargs):
            del kwargs
            self.stop_condition = stop_condition

        async def ainvoke(self, goal: str, thread_id: str | None = None, config: dict | None = None):
            del goal, thread_id, config
            assert self.stop_condition is not None
            assert self.stop_condition() is not None
            return {"messages": [AIMessage(content="terminal failure stop")]}

    monkeypatch.setattr("app.tools.workflow_tools.SessionLocal", lambda: _FakeDb())
    monkeypatch.setattr(
        "app.tools.workflow_tools.get_workflow_session",
        lambda db, session_id: type("Session", (), {"user_id": "user-1"})(),
    )
    monkeypatch.setattr(
        "app.tools.workflow_tools._new_repair_state",
        lambda: {
            "repair_failures": 2,
            "max_repair_failures": 2,
            "active_draft_id": "draft-1",
            "limit_exhausted": True,
            "terminal_failure": {
                "status": "failed",
                "draft_id": "draft-1",
                "repairable": False,
                "error_type": "repair_limit_exceeded",
                "error_summary": "Workflow repair limit reached for draft draft-1. Stop editing and explain the failure to the user.",
                "error": "Workflow repair limit exceeded.",
                "issues": ["root.nodes: invalid shape"],
                "validation_errors": None,
                "details": None,
            },
        },
    )
    monkeypatch.setattr("app.tools.workflow_tools.WorkflowAgent", _FakeWorkflowAgent)
    monkeypatch.setattr(
        "app.workflow.services.agent_response.build_workspace_state",
        lambda db, session_id: {"session_id": session_id, "draft": None, "run": None, "artifacts": []},
    )

    workflow_tool = create_design_workflow_tool(
        model=ToolCallingFakeChatModel(messages=iter([AIMessage(content="Done.")])),
        session_id="session-1",
        system_prompt="test prompt",
        callbacks=[],
        turn_id=None,
    )

    result = await workflow_tool.ainvoke({"goal": "分析附加数据并回答问题"})

    assert result["status"] == "failed"
    assert result["next_action"] == "reply_directly"
    assert result["error_type"] == "repair_limit_exceeded"
    assert "自动修复两次后仍未收敛" in result["final_answer"]
