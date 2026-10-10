"""Prompt and existing event/persistence integration, without a paid model."""

import json
import os
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.agent.prompts import build_supervisor_prompt
from app.knowledge.retrieval import retrieve_knowledge
from app.tasks.analysis_knowledge import publish_knowledge_selection
from app.tasks.callbacks import AgentCallback, MessageCollector
from app.workflow.prompts import build_workflow_prompt
from deepeye.workflows.registry import NodeRegistry


class RecordingEventBus:
    def __init__(self):
        self.events = []

    async def publish(self, channel, message):
        self.events.append((channel, json.loads(message)))


def test_knowledge_reaches_planner_and_supervisor_without_breaking_template_braces():
    context = retrieve_knowledge("CTR下降").prompt_context()
    planner = build_workflow_prompt(NodeRegistry(), knowledge_context=context)
    supervisor = build_supervisor_prompt(knowledge_context=context).format(datasources_context="events.csv")
    for prompt in (planner, supervisor):
        assert "C02" in prompt
        assert "https://doi.org/10.1145/3097983.3098024" in prompt
        assert "Column names alone" in prompt
    assert "events.csv" in supervisor


def test_disabled_context_preserves_original_prompts():
    context = retrieve_knowledge("CTR", enabled=False).prompt_context()
    assert build_workflow_prompt(NodeRegistry(), knowledge_context=context) == build_workflow_prompt(NodeRegistry())
    assert build_supervisor_prompt(knowledge_context=context) == build_supervisor_prompt()


@pytest.mark.asyncio
async def test_reference_step_streams_and_survives_message_serialization():
    selection = retrieve_knowledge("次日留存")
    bus = RecordingEventBus()
    collector = MessageCollector()
    callback = AgentCallback(bus, "test-session", "supervisor", collector=collector)
    await publish_knowledge_selection(callback, selection)
    collector.add_token("supervisor", "请先确认回访定义。")
    message = collector.build()
    assert message.content == "请先确认回访定义。"
    assert len(message.steps) == 1
    assert message.steps[0].name == "analysis_knowledge"
    trace = json.loads(message.model_dump()["steps"][0]["output"])
    assert trace["matches"][0]["id"] == "M02"
    assert trace["matches"][0]["sources"][0]["url"].startswith("https://")
    assert trace["assessment"] == "retrieved_not_adopted_or_validated"
    assert [event[1]["type"] for event in bus.events] == ["tool_start", "tool_end"]


@pytest.mark.asyncio
async def test_disabled_feature_creates_no_step_or_event():
    bus = RecordingEventBus()
    collector = MessageCollector()
    callback = AgentCallback(bus, "test-session", "supervisor", collector=collector)
    await publish_knowledge_selection(callback, retrieve_knowledge("CTR", enabled=False))
    assert not bus.events
    assert not collector.build().steps


@pytest.mark.asyncio
async def test_missing_library_is_visible_but_does_not_replace_answer(tmp_path):
    selection = retrieve_knowledge("CTR", catalog_path=tmp_path / "absent")
    bus = RecordingEventBus()
    collector = MessageCollector()
    callback = AgentCallback(bus, "test-session", "supervisor", collector=collector)
    await publish_knowledge_selection(callback, selection)
    collector.add_token("supervisor", "原有回答")
    message = collector.build()
    assert message.content == "原有回答"
    assert json.loads(message.steps[0].output)["status"] == "unavailable"


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled", [True, False])
@pytest.mark.parametrize("has_data", [True, False])
async def test_actual_task_passes_knowledge_and_persists_reference_step(monkeypatch, enabled, has_data):
    """Run the real task body; fake external LLM, DB, sandbox, Redis boundaries."""
    from app.schemas import AgentInput
    from app.tasks import agent_tasks

    bus = RecordingEventBus()
    captured = {}
    saved = []

    async def no_op(*args, **kwargs):
        pass

    async def unexpected_sandbox(*args, **kwargs):
        assert has_data, "No-data conversation must not require a sandbox"
        captured["sandbox"] = True

    bus.close = no_op
    monkeypatch.setattr(agent_tasks, "_create_model", lambda: object())
    monkeypatch.setattr(agent_tasks, "RedisEventBus", lambda url: bus)
    monkeypatch.setattr(agent_tasks, "get_user_id", lambda sid: "test-user")
    monkeypatch.setattr(agent_tasks, "persist_message", lambda sid, message: saved.append(message) or SimpleNamespace(id="message"))
    monkeypatch.setattr(agent_tasks, "create_chat_turn_record", lambda *a, **kw: SimpleNamespace(id="turn"))
    monkeypatch.setattr(agent_tasks, "complete_chat_turn_record", lambda *a, **kw: None)
    monkeypatch.setattr(agent_tasks, "fail_chat_turn_record", lambda *a, **kw: pytest.fail("Task failed"))
    monkeypatch.setattr(agent_tasks, "sandbox_manager", SimpleNamespace(get_or_create_sandbox=unexpected_sandbox))
    monkeypatch.setattr(agent_tasks, "list_file_datasources", lambda *a: [])
    monkeypatch.setattr(agent_tasks, "get_datasources_info", lambda *a: [])
    monkeypatch.setattr(agent_tasks, "get_datasources_schema", lambda *a: [])
    monkeypatch.setattr(agent_tasks, "build_registry", NodeRegistry)
    monkeypatch.setattr(agent_tasks.settings, "ANALYSIS_KNOWLEDGE_ENABLED", enabled)

    def design_tool(model, sid, prompt, **kwargs):
        captured["planner"] = prompt
        return object()

    monkeypatch.setattr(agent_tasks, "create_design_workflow_tool", design_tool)
    monkeypatch.setattr(agent_tasks, "create_summarize_workflow_result_tool", lambda *a, **kw: object())

    @asynccontextmanager
    async def checkpointer(*args):
        yield SimpleNamespace(setup=no_op)

    monkeypatch.setattr(agent_tasks, "AsyncPostgresSaver", SimpleNamespace(from_conn_string=checkpointer))

    class Factory:
        def __init__(self, *args):
            pass

        def create_supervisor(self, tools, system_prompt_template):
            assert len(tools) == (2 if has_data else 0)
            captured["supervisor"] = system_prompt_template.format(datasources_context="No data")
            return self

        async def ainvoke(self, question, thread_id, config):
            await config["callbacks"][0].on_llm_new_token("先确认留存口径。")

    monkeypatch.setattr(agent_tasks, "AgentFactory", Factory)
    await agent_tasks._run_agent_async(AgentInput(session_id="test-session", user_input="次日留存怎么算？", datasource_ids=["test-data"] if has_data else []))
    assert ("sandbox" in captured) is has_data
    if has_data:
        assert ("M02" in captured["planner"]) is enabled
    else:
        assert "planner" not in captured
    assert ("M02" in captured["supervisor"]) is enabled
    assert saved[-1].content == "先确认留存口径。"
    assert bool(saved[-1].steps) is enabled
    assert bus.events[-1][1]["type"] == "agent_end"
