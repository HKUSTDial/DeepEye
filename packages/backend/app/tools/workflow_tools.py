from __future__ import annotations

import copy
import json
import re
import uuid
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.db.session import SessionLocal
from app.repositories import SessionRepository
from app.sandbox import sandbox_manager
from app.services.agent_prompts import build_workflow_summary_prompt
from app.services.workflow_datasets import compact_value_for_transport, compact_workflow_result
from app.services.workflow_file_service import (
    service_run_workflow_draft,
    service_run_workflow_from_file,
    write_workflow_definition_to_file,
)
from app.services.workflow_targets import normalize_workflow_path, save_workflow_draft, resolve_workflow_target
from app.services.workflow_tracking_service import build_workspace_state, build_workspace_state_for_turn
from deepeye.agents import WorkflowAgent
from deepeye.tools.base import tool
from deepeye.utils.logger import logger

_MAX_REPAIR_ATTEMPTS = 2
_ARTIFACT_NODE_TYPES = {"report.generate", "data.generate_dashboard", "video.generator"}
_DATASET_PRODUCER_NODE_TYPES = {
    "datasource.read",
    "sql.execute",
    "python.code",
    "rows.select",
    "rows.filter",
    "rows.sort",
    "rows.aggregate",
    "rows.profile",
}


def _get_session(db, session_id: str):
    try:
        session_uuid = uuid.UUID(session_id)
    except (TypeError, ValueError):
        logger.warning("[workflow_tools] Invalid session_id=%s", session_id)
        return None
    return SessionRepository(db).get(session_uuid)


async def _read_workflow_file(session_id: str, path: str) -> dict:
    sandbox = await sandbox_manager.get_or_create_sandbox(session_id)
    if not sandbox:
        raise ValueError("failed to get or create sandbox")
    result = await sandbox.exec_command(f"cat {path}")
    if result.exit_code != 0:
        raise ValueError(result.stderr or "failed to read workflow file")
    if not result.stdout.strip():
        raise ValueError("workflow file is empty")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid workflow json: {exc}") from exc


def _serialize_workspace_state(snapshot: dict) -> dict:
    turn = snapshot.get("turn")
    draft = snapshot.get("draft")
    run = snapshot.get("run")
    artifacts = snapshot.get("artifacts") or []
    return {
        "session_id": str(snapshot.get("session_id")) if snapshot.get("session_id") is not None else None,
        "turn": (
            {
                "id": str(turn.id),
                "status": turn.status,
                "input_text": turn.input_text,
                "error": turn.error,
            }
            if turn
            else None
        ),
        "draft": (
            {
                "id": str(draft.id),
                "status": draft.status,
                "version": draft.version,
                "source": draft.source,
            }
            if draft
            else None
        ),
        "run": (
            {
                "id": str(run.id),
                "status": run.status,
                "error": run.error,
                "result": compact_workflow_result(run.result, row_limit=10, text_limit=2500),
            }
            if run
            else None
        ),
        "artifacts": [
            {
                "id": str(artifact.id),
                "kind": artifact.kind,
                "payload": compact_value_for_transport(artifact.payload, row_limit=10, text_limit=2500),
            }
            for artifact in artifacts
        ],
    }


def _extract_final_answer(workspace_state: dict | None) -> str | None:
    if not isinstance(workspace_state, dict):
        return None
    run = workspace_state.get("run")
    if not isinstance(run, dict):
        return None
    result = run.get("result")
    if not isinstance(result, dict):
        return None
    outputs = result.get("outputs")
    if not isinstance(outputs, dict):
        return None
    for node_output in outputs.values():
        if not isinstance(node_output, dict):
            continue
        answer = node_output.get("answer")
        if isinstance(answer, str) and answer.strip():
            return answer.strip()
    return None


def _summarize_issue(issue: Any) -> str:
    if isinstance(issue, dict):
        code = issue.get("code")
        message = issue.get("message")
        location = issue.get("location") or issue.get("loc")
        location_text = ""
        if isinstance(location, list) and location:
            location_text = ".".join(str(part) for part in location)
        elif isinstance(location, str) and location:
            location_text = location
        parts = [str(part) for part in (code, message) if isinstance(part, str) and part]
        summary = ": ".join(parts) if parts else json.dumps(issue, ensure_ascii=False)
        return f"{location_text}: {summary}" if location_text else summary
    return str(issue)


def _summarize_issues(issues: list[Any] | None, *, limit: int = 3) -> list[str]:
    if not isinstance(issues, list):
        return []
    return [_summarize_issue(issue) for issue in issues[:limit]]


def _workflow_nodes(workflow_definition: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(workflow_definition, dict):
        return {}
    root = workflow_definition.get("root")
    if not isinstance(root, dict):
        return {}
    nodes = root.get("nodes")
    if not isinstance(nodes, dict):
        return {}
    return {node_id: node for node_id, node in nodes.items() if isinstance(node, dict)}


def _workflow_edges(workflow_definition: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(workflow_definition, dict):
        return {}
    root = workflow_definition.get("root")
    if not isinstance(root, dict):
        return {}
    edges = root.get("edges")
    if not isinstance(edges, dict):
        return {}
    return {edge_id: edge for edge_id, edge in edges.items() if isinstance(edge, dict)}


def _candidate_dataset_sources(
    workflow_definition: dict[str, Any] | None,
    *,
    exclude_node_id: str | None = None,
) -> list[str]:
    nodes = _workflow_nodes(workflow_definition)
    if not nodes:
        return []

    producers = [
        node_id
        for node_id, node in nodes.items()
        if (not exclude_node_id or node_id != exclude_node_id)
        and node.get("type") in _DATASET_PRODUCER_NODE_TYPES
    ]
    if not producers:
        return []

    producer_set = set(producers)
    downstream_producers: set[str] = set()
    for edge in _workflow_edges(workflow_definition).values():
        source = edge.get("source")
        target = edge.get("target")
        if not isinstance(source, dict) or not isinstance(target, dict):
            continue
        source_node_id = source.get("node_id")
        target_node_id = target.get("node_id")
        if source_node_id in producer_set and target_node_id in producer_set:
            downstream_producers.add(source_node_id)

    terminal_producers = [node_id for node_id in producers if node_id not in downstream_producers]
    return terminal_producers or producers


def _ordered_node_ids(workflow_definition: dict[str, Any] | None) -> list[str]:
    return list(_workflow_nodes(workflow_definition).keys())


def _incoming_dataset_sources(
    workflow_definition: dict[str, Any] | None,
    *,
    node_id: str,
    port_id: str = "dataset_ref",
) -> list[str]:
    incoming_sources: list[str] = []
    for edge in _workflow_edges(workflow_definition).values():
        source = edge.get("source")
        target = edge.get("target")
        if not isinstance(source, dict) or not isinstance(target, dict):
            continue
        if target.get("node_id") != node_id or target.get("port_id") != port_id:
            continue
        source_node_id = source.get("node_id")
        source_port_id = source.get("port_id")
        if not isinstance(source_node_id, str) or source_port_id != "dataset_ref":
            continue
        incoming_sources.append(source_node_id)
    return incoming_sources


def _dataset_ref_repair_hint(
    *,
    workflow_definition: dict[str, Any] | None,
    node_id: str,
) -> tuple[str, str]:
    incoming_sources = _incoming_dataset_sources(workflow_definition, node_id=node_id)
    nodes = _workflow_nodes(workflow_definition)
    if incoming_sources:
        source_list = ", ".join(f"`{source}`" for source in incoming_sources[:3])
        hint = (
            f"Node {node_id} already has incoming dataset_ref edge(s) from {source_list}, "
            "but those upstream node outputs did not contain a usable dataset_ref at runtime. "
            "Fix the upstream node so it actually emits `dataset_ref`."
        )
        if len(incoming_sources) == 1 and nodes.get(incoming_sources[0], {}).get("type") == "python.code":
            hint += (
                f" Update `{incoming_sources[0]}` so it prints tabular JSON rows "
                "or an explicit dataset_ref object instead of narrative text."
            )
            upstream_sources = _incoming_dataset_sources(workflow_definition, node_id=incoming_sources[0])
            if upstream_sources:
                source_list = ", ".join(f"`{source}`" for source in upstream_sources[:3])
                hint += (
                    f" If `{incoming_sources[0]}` is only producing narrative analysis, remove it and connect "
                    f"{source_list}.dataset_ref directly to `{node_id}`."
                )
        else:
            hint += (
                " If the upstream step is `python.code`, make it print tabular JSON rows "
                "or an explicit dataset_ref object instead of prose."
            )
        return "workflow_dataset_output_missing", hint

    candidates = _candidate_dataset_sources(workflow_definition, exclude_node_id=node_id)
    if candidates:
        ordered_node_ids = _ordered_node_ids(workflow_definition)
        if node_id in ordered_node_ids:
            target_index = ordered_node_ids.index(node_id)
            ordered_candidates = sorted(
                candidates,
                key=lambda candidate_id: (
                    ordered_node_ids.index(candidate_id)
                    if candidate_id in ordered_node_ids
                    else -1
                ),
            )
            ordered_candidates = [
                candidate_id
                for candidate_id in ordered_candidates
                if candidate_id in ordered_node_ids
                and ordered_node_ids.index(candidate_id) < target_index
            ] or ordered_candidates
        else:
            ordered_candidates = candidates
        if len(ordered_candidates) == 1:
            hint = f"Connect {ordered_candidates[0]}.dataset_ref -> {node_id}.dataset_ref."
        else:
            joined = ", ".join(f"{candidate}.dataset_ref" for candidate in ordered_candidates[:3])
            hint = f"Connect one upstream dataset output ({joined}) to {node_id}.dataset_ref."
    else:
        hint = f"Add an incoming edge from an upstream dataset-producing node to {node_id}.dataset_ref."
    return "workflow_dataset_input_missing", hint


def _artifact_input_missing_failure(
    *,
    draft_id: str | None,
    run_id: str | None,
    details: list[Any],
    error: str | None,
    workflow_definition: dict[str, Any] | None,
) -> dict[str, Any] | None:
    for detail in details:
        if not isinstance(detail, dict):
            continue
        node_id = detail.get("node_id")
        node_type = detail.get("node_type")
        message = detail.get("message")
        if not isinstance(node_id, str) or not isinstance(node_type, str) or not isinstance(message, str):
            continue
        lower_message = message.lower()
        if node_type not in _ARTIFACT_NODE_TYPES:
            continue
        if "dataset_ref input is required" not in lower_message and "required input missing" not in lower_message:
            continue
        error_type, hint = _dataset_ref_repair_hint(
            workflow_definition=workflow_definition,
            node_id=node_id,
        )
        summary = (
            f"Artifact node {node_id} ({node_type}) is missing its required dataset_ref input. {hint}"
        )
        failure = _build_tool_failure(
            draft_id=draft_id,
            run_id=run_id,
            error_type="workflow_artifact_input_missing"
            if error_type == "workflow_dataset_input_missing"
            else error_type,
            error_summary=summary,
            repairable=True,
            details=details,
            error=error,
        )
        failure["issues"] = [hint]
        return failure
    return None


def _dataset_input_missing_failure(
    *,
    draft_id: str | None,
    run_id: str | None,
    details: list[Any],
    error: str | None,
    workflow_definition: dict[str, Any] | None,
) -> dict[str, Any] | None:
    for detail in details:
        if not isinstance(detail, dict):
            continue
        node_id = detail.get("node_id")
        node_type = detail.get("node_type")
        message = detail.get("message")
        if not isinstance(node_id, str) or not isinstance(node_type, str) or not isinstance(message, str):
            continue
        lower_message = message.lower()
        if "dataset_ref input is required" not in lower_message and "required input missing" not in lower_message:
            continue
        error_type, hint = _dataset_ref_repair_hint(
            workflow_definition=workflow_definition,
            node_id=node_id,
        )
        summary = f"Node {node_id} ({node_type}) is missing its required dataset_ref input. {hint}"
        failure = _build_tool_failure(
            draft_id=draft_id,
            run_id=run_id,
            error_type=error_type,
            error_summary=summary,
            repairable=True,
            details=details,
            error=error,
        )
        failure["issues"] = [hint]
        return failure
    return None


def _definition_wiring_failure(
    *,
    draft_id: str | None,
    run_id: str | None,
    details: list[Any],
    error: str | None,
) -> dict[str, Any] | None:
    for detail in details:
        if not isinstance(detail, dict):
            continue
        loc = detail.get("loc")
        msg = detail.get("msg")
        if not isinstance(msg, str):
            continue
        if (
            isinstance(loc, list)
            and len(loc) >= 4
            and loc[0] == "nodes"
            and loc[2] == "inputs"
            and "Input should be a valid dictionary or instance of Port" in msg
        ):
            node_id = str(loc[1])
            port_id = str(loc[3])
            summary = (
                f"Workflow wiring is invalid for {node_id}.{port_id}. Do not place incoming edge endpoints inside "
                f"`node.inputs`. Omit node-level `inputs`/`outputs` unless you are copying the registry spec exactly, "
                f"and express data flow only through `root.edges`."
            )
            failure = _build_tool_failure(
                draft_id=draft_id,
                run_id=run_id,
                error_type="workflow_wiring_invalid",
                error_summary=summary,
                repairable=True,
                details=details,
                error=error,
            )
            failure["issues"] = [
                f"Remove the invalid `inputs.{port_id}` block from node `{node_id}` and connect upstream nodes through `root.edges` only."
            ]
            return failure
        location_text = ".".join(str(part) for part in loc) if isinstance(loc, list) else str(loc or "")
        if "edge.source.port.missing" in location_text or "Source port missing: input" in msg:
            summary = (
                "Workflow wiring is invalid because an edge is using an input port as its source. "
                "Edges must originate from output ports such as `dataset_ref`, never from an input port like `input`."
            )
            failure = _build_tool_failure(
                draft_id=draft_id,
                run_id=run_id,
                error_type="workflow_wiring_invalid",
                error_summary=summary,
                repairable=True,
                details=details,
                error=error,
            )
            failure["issues"] = [
                "Change the edge source port to a real upstream output port, usually `dataset_ref`, and keep `input` only on the target side."
            ]
            return failure
    return None


def _sql_query_failure(
    *,
    draft_id: str | None,
    run_id: str | None,
    details: list[Any],
    error: str | None,
) -> dict[str, Any] | None:
    for detail in details:
        if not isinstance(detail, dict):
            continue
        node_id = detail.get("node_id")
        node_type = detail.get("node_type")
        message = detail.get("message")
        if not isinstance(node_id, str) or node_type != "sql.execute" or not isinstance(message, str):
            continue
        lower_message = message.lower()
        if not any(
            token in lower_message
            for token in (
                "does not exist",
                "undefinedcolumn",
                "undefinedtable",
                "syntax error",
                "missing from-clause",
                "ambiguous",
            )
        ):
            continue
        failure = _build_tool_failure(
            draft_id=draft_id,
            run_id=run_id,
            error_type="workflow_sql_query_invalid",
            error_summary=(
                f"SQL query in node {node_id} is invalid for the attached database schema. "
                "Fix the query and reuse the same draft_id."
            ),
            repairable=True,
            details=details,
            error=error,
        )
        failure["issues"] = [
            "Use only tables and columns from the attached database schema inside `sql.execute`.",
            "Do not reference file-only columns inside SQL. If the analysis needs both file fields and database fields, query the database-native columns in `sql.execute` and join with file data in `python.code`.",
            "Add explicit `AS` aliases for every derived or aggregated SQL output column used downstream.",
        ]
        return failure
    return None


def _python_schema_failure(
    *,
    draft_id: str | None,
    run_id: str | None,
    details: list[Any],
    error: str | None,
) -> dict[str, Any] | None:
    def _extract_available_columns(error_text: str | None) -> list[str]:
        if not isinstance(error_text, str) or "INPUT_PREVIEW" not in error_text:
            return []
        match = re.search(r'"columns"\s*:\s*\[(.*?)\]', error_text, re.DOTALL)
        if not match:
            return []
        columns_blob = match.group(1)
        return [
            column
            for column in re.findall(r'"([^"]+)"', columns_blob)
            if isinstance(column, str) and column.strip()
        ]

    available_columns = _extract_available_columns(error)

    for detail in details:
        if not isinstance(detail, dict):
            continue
        node_id = detail.get("node_id")
        node_type = detail.get("node_type")
        message = detail.get("message")
        if not isinstance(node_id, str) or node_type != "python.code" or not isinstance(message, str):
            continue
        lower_message = message.lower()
        if not any(
            token in lower_message
            for token in (
                "keyerror",
                "column not found",
                "no such column",
            )
        ):
            continue
        failure = _build_tool_failure(
            draft_id=draft_id,
            run_id=run_id,
            error_type="workflow_python_schema_invalid",
            error_summary=(
                f"python.code node {node_id} referenced columns that were not present in its upstream dataset inputs. "
                "Fix the code to use the actual upstream schema and reuse the same draft_id."
            ),
            repairable=True,
            details=details,
            error=error,
        )
        failure["issues"] = [
            "Use only column names that actually appear in upstream `dataset_ref.columns` or preview rows.",
            "If an upstream `sql.execute` query uses `AS` aliases or aggregates columns, downstream `python.code` must reference those exact output names, not the original source column names.",
            "Inside `python.code`, inspect `data.get('dataset_ref', [])` metadata first and align every join, groupby, and calculation to the emitted schema.",
        ]
        if available_columns:
            failure["issues"].append(
                "Upstream preview columns currently visible are: "
                + ", ".join(f"`{column}`" for column in available_columns[:12])
                + "."
            )
        return failure
    return None


def _build_tool_failure(
    *,
    draft_id: str | None = None,
    run_id: str | None = None,
    error_type: str,
    error_summary: str,
    repairable: bool,
    validation_errors: list[Any] | None = None,
    details: list[Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    issues = _summarize_issues(validation_errors) or _summarize_issues(details)
    return {
        "status": "failed",
        "draft_id": draft_id,
        "run_id": run_id,
        "repairable": repairable,
        "error_type": error_type,
        "error_summary": error_summary,
        "validation_errors": validation_errors,
        "details": details,
        "error": error,
        "issues": issues,
    }


def _contains_cjk(text: str | None) -> bool:
    if not isinstance(text, str):
        return False
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def _normalize_indexed_items(value: Any) -> Any:
    if not isinstance(value, list):
        return value
    normalized: dict[str, Any] = {}
    for item in value:
        if not isinstance(item, dict):
            return value
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id:
            return value
        normalized[item_id] = item
    return normalized


def _parse_json_object_string(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text or text[0] not in "{[":
        return value
    try:
        return json.loads(text)
    except Exception:
        return value


def _normalize_workflow_payload_shape(workflow: dict[str, Any] | str) -> dict[str, Any] | Any:
    workflow = _parse_json_object_string(workflow)
    if not isinstance(workflow, dict):
        return workflow
    normalized = copy.deepcopy(workflow)
    normalized["root"] = _parse_json_object_string(normalized.get("root"))
    root = normalized.get("root")
    if not isinstance(root, dict):
        return normalized
    root["nodes"] = _parse_json_object_string(root.get("nodes"))
    root["edges"] = _parse_json_object_string(root.get("edges"))
    root["nodes"] = _normalize_indexed_items(root.get("nodes"))
    root["edges"] = _normalize_indexed_items(root.get("edges"))
    return normalized


def _normalize_workflow_run_result(
    run_result: dict[str, Any],
    *,
    draft_id: str | None,
    workflow_definition: dict[str, Any] | None = None,
) -> dict[str, Any]:
    status = run_result.get("status") or "failed"
    run_id = run_result.get("run_id")
    artifacts = run_result.get("artifacts") if isinstance(run_result.get("artifacts"), list) else []
    if status == "success":
        return {
            "status": "success",
            "draft_id": draft_id,
            "run_id": run_id,
            "repairable": False,
            "error_type": None,
            "error_summary": None,
            "validation_errors": None,
            "details": None,
            "error": None,
            "issues": [],
            "artifacts": artifacts,
            "final_answer_present": _extract_final_answer(
                {"run": {"result": {"outputs": run_result.get("outputs", {})}}}
            )
            is not None,
        }

    validation_errors = run_result.get("validation_errors")
    details = run_result.get("details")
    error = run_result.get("error")
    if isinstance(validation_errors, list) and validation_errors:
        return {
            **_build_tool_failure(
                draft_id=draft_id,
                run_id=run_id,
                error_type="workflow_validation_failed",
                error_summary="Workflow validation failed. Reuse the same draft_id and fix only the reported issues.",
                repairable=True,
                validation_errors=validation_errors,
                error=error,
            ),
            "artifacts": artifacts,
        }
    if isinstance(details, list) and details:
        artifact_failure = _artifact_input_missing_failure(
            draft_id=draft_id,
            run_id=run_id,
            details=details,
            error=error,
            workflow_definition=workflow_definition,
        )
        if artifact_failure:
            artifact_failure["artifacts"] = artifacts
            return artifact_failure
        dataset_input_failure = _dataset_input_missing_failure(
            draft_id=draft_id,
            run_id=run_id,
            details=details,
            error=error,
            workflow_definition=workflow_definition,
        )
        if dataset_input_failure:
            dataset_input_failure["artifacts"] = artifacts
            return dataset_input_failure
        sql_failure = _sql_query_failure(
            draft_id=draft_id,
            run_id=run_id,
            details=details,
            error=error,
        )
        if sql_failure:
            sql_failure["artifacts"] = artifacts
            return sql_failure
        python_failure = _python_schema_failure(
            draft_id=draft_id,
            run_id=run_id,
            details=details,
            error=error,
        )
        if python_failure:
            python_failure["artifacts"] = artifacts
            return python_failure
    if isinstance(details, list) and details and all(
        isinstance(item, dict) and "node_id" in item and "message" in item for item in details
    ):
        return {
            **_build_tool_failure(
                draft_id=draft_id,
                run_id=run_id,
                error_type="workflow_execution_failed",
                error_summary=(error or "Workflow execution failed."),
                repairable=False,
                details=details,
                error=error,
            ),
            "artifacts": artifacts,
        }
    if isinstance(details, list) and details:
        wiring_failure = _definition_wiring_failure(
            draft_id=draft_id,
            run_id=run_id,
            details=details,
            error=error,
        )
        if wiring_failure:
            wiring_failure["artifacts"] = artifacts
            return wiring_failure
        return {
            **_build_tool_failure(
                draft_id=draft_id,
                run_id=run_id,
                error_type="workflow_definition_invalid",
                error_summary="Workflow definition is invalid. Reuse the same draft_id and fix the invalid fields only.",
                repairable=True,
                details=details,
                error=error,
            ),
            "artifacts": artifacts,
        }
    return {
        **_build_tool_failure(
            draft_id=draft_id,
            run_id=run_id,
            error_type="workflow_execution_failed",
            error_summary=(error or "Workflow execution failed."),
            repairable=False,
            error=error,
        ),
        "artifacts": artifacts,
    }


def _new_repair_state() -> dict[str, Any]:
    return {
        "repair_failures": 0,
        "max_repair_failures": _MAX_REPAIR_ATTEMPTS,
        "active_draft_id": None,
        "limit_exhausted": False,
        "terminal_failure": None,
    }


def _mark_terminal_failure(state: dict[str, Any], failure: dict[str, Any]) -> dict[str, Any]:
    state["terminal_failure"] = failure
    return failure


def _repair_limit_failure(state: dict[str, Any], last_failure: dict[str, Any] | None = None) -> dict[str, Any]:
    draft_id = state.get("active_draft_id")
    failure = _build_tool_failure(
        draft_id=draft_id,
        error_type="repair_limit_exceeded",
        error_summary=f"Workflow repair limit reached for draft {draft_id}. Stop editing and explain the failure to the user.",
        repairable=False,
        error="Workflow repair limit exceeded.",
    )
    if isinstance(last_failure, dict):
        prior_issues = last_failure.get("issues")
        if isinstance(prior_issues, list) and prior_issues:
            failure["issues"] = prior_issues
        if isinstance(last_failure.get("error"), str) and last_failure["error"]:
            failure["details"] = last_failure.get("details")
            failure["validation_errors"] = last_failure.get("validation_errors")
    return _mark_terminal_failure(state, failure)


def _guard_repair_limit(state: dict[str, Any]) -> dict[str, Any] | None:
    if state.get("limit_exhausted"):
        return _repair_limit_failure(state)
    return None


def _register_repairable_failure(state: dict[str, Any], draft_id: str | None) -> dict[str, Any] | None:
    state["repair_failures"] = int(state.get("repair_failures", 0)) + 1
    if draft_id:
        state["active_draft_id"] = draft_id
    state["terminal_failure"] = None
    if state["repair_failures"] >= int(state.get("max_repair_failures", _MAX_REPAIR_ATTEMPTS)):
        state["limit_exhausted"] = True
        return None
    return None


def _note_successful_run(state: dict[str, Any], draft_id: str | None) -> None:
    if draft_id:
        state["active_draft_id"] = draft_id
    state["terminal_failure"] = None


def _require_reuse_after_failure(state: dict[str, Any], draft_id: str | None) -> dict[str, Any] | None:
    active_draft_id = state.get("active_draft_id")
    repair_failures = int(state.get("repair_failures", 0))
    if repair_failures <= 0 or not active_draft_id:
        return None
    if draft_id == active_draft_id:
        return None
    return _build_tool_failure(
        draft_id=active_draft_id,
        error_type="draft_reuse_required",
        error_summary=f"Reuse the existing draft_id {active_draft_id} after a failed run instead of creating a new workflow.",
        repairable=True,
        error="Draft reuse required after a failed workflow run.",
    )


def _terminal_failure_reply(goal: str, failure: dict[str, Any]) -> str:
    summary = failure.get("error_summary") or failure.get("error") or "Workflow planning stopped."
    if _contains_cjk(goal):
        if failure.get("error_type") == "repair_limit_exceeded":
            return "工作流规划在自动修复两次后仍未收敛，系统已停止继续修改。请补充更明确的目标或检查数据结构后重试。"
        if failure.get("error_type") == "workflow_definition_invalid":
            return "自动生成的工作流结构无效，系统已停止继续修改。请补充更明确的目标或稍后重试。"
        return f"工作流规划已停止：{summary}"
    if failure.get("error_type") == "repair_limit_exceeded":
        return "Workflow planning did not converge after two automatic repair attempts. Please clarify the goal or retry with a narrower request."
    if failure.get("error_type") == "workflow_definition_invalid":
        return "The generated workflow structure was invalid, so planning stopped. Please clarify the goal or retry."
    return f"Workflow planning stopped: {summary}"


def create_create_workflow_tool(session_id: str, user_id: str, turn_id: str | None = None) -> callable:
    @tool
    async def create_workflow(
        workflow: dict,
        draft_id: str | None = None,
        name: str | None = None,
        file_path: str | None = None,
        planning_notes: str | None = None,
    ) -> dict:
        """
        Create a workflow draft or replace an existing draft.

        Args:
            workflow: The full workflow definition object.
            draft_id: Existing workflow draft id to update.
            name: Optional logical workflow name. Used to derive file path if needed.
            file_path: Optional explicit legacy sandbox workflow file path. Prefer draft_id or name.
            planning_notes: Concise step-by-step planning notes explaining nodes, schemas, and edges.
        """
        workflow = _normalize_workflow_payload_shape(workflow)
        db = SessionLocal()
        try:
            draft = save_workflow_draft(
                db,
                session_id=session_id,
                user_id=user_id,
                definition=workflow,
                turn_id=turn_id,
                draft_id=draft_id,
                file_path=file_path,
                name=name,
                source="workflow_agent",
            )
        finally:
            db.close()

        norm_path = draft.file_path or normalize_workflow_path(file_path or name or "workflow.json")
        await write_workflow_definition_to_file(session_id, norm_path, workflow)
        return {"status": "success", "draft_id": str(draft.id)}

    return create_workflow


def create_read_workflow_tool(session_id: str) -> callable:
    @tool
    async def read_workflow(draft_id: str | None = None, file_path: str | None = None) -> dict:
        """
        Read an existing workflow draft.

        Args:
            draft_id: Workflow draft id. Preferred.
            file_path: Explicit legacy sandbox workflow JSON file path. Fallback only.
        """
        if not draft_id and not file_path:
            return {"status": "error", "error": "Provide draft_id. Use file_path only for an explicit legacy workflow file."}

        db = SessionLocal()
        try:
            existing_draft, norm_path = resolve_workflow_target(
                db,
                session_id,
                draft_id=draft_id,
                file_path=file_path,
            )
            if existing_draft and isinstance(existing_draft.definition, dict) and existing_draft.definition:
                return {
                    "status": "success",
                    "workflow": existing_draft.definition,
                    "draft_id": str(existing_draft.id),
                }
        finally:
            db.close()

        try:
            workflow = await _read_workflow_file(session_id, norm_path)
            return {"status": "success", "workflow": workflow, "draft_id": draft_id}
        except Exception as exc:
            return {"status": "error", "error": str(exc), "draft_id": draft_id}

    return read_workflow


def create_update_workflow_tool(
    session_id: str,
    user_id: str,
    turn_id: str | None = None,
    repair_state: dict[str, Any] | None = None,
) -> callable:
    @tool
    async def update_workflow(
        workflow: dict,
        draft_id: str | None = None,
        name: str | None = None,
        file_path: str | None = None,
        planning_notes: str | None = None,
    ) -> dict:
        """
        Update an existing workflow draft or overwrite a file-backed workflow.

        Args:
            workflow: The full workflow definition object.
            draft_id: Existing workflow draft id to update.
            name: Optional logical workflow name. Used to derive file path if needed.
            file_path: Optional explicit legacy sandbox workflow file path. Prefer draft_id.
            planning_notes: Concise step-by-step planning notes explaining nodes, schemas, and edges.
        """
        if repair_state:
            blocked = _guard_repair_limit(repair_state)
            if blocked:
                return blocked
            reuse_failure = _require_reuse_after_failure(repair_state, draft_id)
            if reuse_failure:
                return reuse_failure
        workflow = _normalize_workflow_payload_shape(workflow)
        db = SessionLocal()
        try:
            draft = save_workflow_draft(
                db,
                session_id=session_id,
                user_id=user_id,
                definition=workflow,
                turn_id=turn_id,
                draft_id=draft_id,
                file_path=file_path,
                name=name,
                source="workflow_agent",
            )
        finally:
            db.close()

        norm_path = draft.file_path or normalize_workflow_path(file_path or name or "workflow.json")
        await write_workflow_definition_to_file(session_id, norm_path, workflow)
        return {"status": "success", "draft_id": str(draft.id)}

    return update_workflow


def create_run_workflow_from_file_tool(session_id: str, turn_id: str | None = None) -> callable:
    @tool
    async def run_workflow_from_file(file_path: str) -> dict:
        """
        Run a workflow directly from a known sandbox file path.

        Args:
            file_path: Workflow JSON file path for an explicitly file-based workflow.
        """
        db = SessionLocal()
        try:
            session = _get_session(db, session_id)
            if not session:
                return {"status": "error", "error": "Session not found."}
            _, norm_path = resolve_workflow_target(
                db,
                session_id,
                file_path=file_path,
            )
            return await service_run_workflow_from_file(
                db,
                session.user_id,
                session_id,
                norm_path,
                turn_id=turn_id,
            )
        finally:
            db.close()

    return run_workflow_from_file


def create_run_workflow_tool(
    session_id: str,
    turn_id: str | None = None,
    repair_state: dict[str, Any] | None = None,
) -> callable:
    @tool
    async def run_workflow(draft_id: str) -> dict:
        """
        Run a workflow draft by id.

        Args:
            draft_id: Workflow draft id to execute.
        """
        if repair_state:
            blocked = _guard_repair_limit(repair_state)
            if blocked:
                return blocked
            reuse_failure = _require_reuse_after_failure(repair_state, draft_id)
            if reuse_failure:
                return reuse_failure
        db = SessionLocal()
        try:
            session = _get_session(db, session_id)
            if not session:
                failure = _build_tool_failure(
                    draft_id=draft_id,
                    error_type="session_not_found",
                    error_summary="Session not found.",
                    repairable=False,
                    error="Session not found.",
                )
                if repair_state:
                    return _mark_terminal_failure(repair_state, failure)
                return failure
            existing_draft, norm_path = resolve_workflow_target(
                db,
                session_id,
                draft_id=draft_id,
            )
            if not existing_draft or not isinstance(existing_draft.definition, dict):
                failure = _build_tool_failure(
                    draft_id=draft_id,
                    error_type="draft_not_found",
                    error_summary="Workflow draft not found.",
                    repairable=False,
                    error="Workflow draft not found.",
                )
                if repair_state:
                    return _mark_terminal_failure(repair_state, failure)
                return failure
            result = await service_run_workflow_draft(
                db,
                session.user_id,
                session_id,
                str(existing_draft.id),
                turn_id=turn_id,
            )
            normalized = _normalize_workflow_run_result(
                result,
                draft_id=str(existing_draft.id),
                workflow_definition=existing_draft.definition,
            )
            if repair_state:
                if normalized["status"] == "success":
                    _note_successful_run(repair_state, str(existing_draft.id))
                elif normalized["repairable"]:
                    limit_failure = _register_repairable_failure(repair_state, str(existing_draft.id))
                    if limit_failure:
                        return limit_failure
                    if repair_state.get("limit_exhausted"):
                        return _repair_limit_failure(repair_state, normalized)
                else:
                    return _mark_terminal_failure(repair_state, normalized)
            return normalized
        finally:
            db.close()

    return run_workflow


def create_workflow_and_run_tool(
    session_id: str,
    turn_id: str | None = None,
    repair_state: dict[str, Any] | None = None,
) -> callable:
    """Single tool: create/update a workflow draft and run it immediately."""

    @tool
    async def create_workflow_and_run(
        workflow: dict,
        draft_id: str | None = None,
        name: str | None = None,
        file_path: str | None = None,
        planning_notes: str | None = None,
    ) -> dict:
        """
        Create or update a workflow draft and run it immediately.

        Args:
            workflow: Full workflow with root.nodes and root.edges.
            draft_id: Existing workflow draft id to update and execute.
            name: Optional logical workflow name. Used to derive file path if needed.
            file_path: Optional explicit legacy sandbox workflow file path. Prefer name or draft_id.
            planning_notes: Concise step-by-step planning notes explaining nodes, schemas, and edges.
        """
        if repair_state:
            blocked = _guard_repair_limit(repair_state)
            if blocked:
                return blocked
            reuse_failure = _require_reuse_after_failure(repair_state, draft_id)
            if reuse_failure:
                return reuse_failure
        workflow = _normalize_workflow_payload_shape(workflow)
        db = SessionLocal()
        try:
            session = _get_session(db, session_id)
            if not session:
                failure = _build_tool_failure(
                    draft_id=draft_id,
                    error_type="session_not_found",
                    error_summary="Session not found.",
                    repairable=False,
                    error="Session not found.",
                )
                if repair_state:
                    return _mark_terminal_failure(repair_state, failure)
                return failure
            draft = save_workflow_draft(
                db,
                session_id=session_id,
                user_id=str(session.user_id),
                definition=workflow,
                turn_id=turn_id,
                draft_id=draft_id,
                file_path=file_path,
                name=name,
                source="workflow_agent",
            )
            result = await service_run_workflow_draft(
                db,
                session.user_id,
                session_id,
                str(draft.id),
                turn_id=turn_id,
            )
            normalized = _normalize_workflow_run_result(
                result,
                draft_id=str(draft.id),
                workflow_definition=workflow,
            )
            if repair_state:
                if normalized["status"] == "success":
                    _note_successful_run(repair_state, str(draft.id))
                elif normalized["repairable"]:
                    limit_failure = _register_repairable_failure(repair_state, str(draft.id))
                    if limit_failure:
                        return limit_failure
                    if repair_state.get("limit_exhausted"):
                        return _repair_limit_failure(repair_state, normalized)
                else:
                    return _mark_terminal_failure(repair_state, normalized)
            return normalized
        finally:
            db.close()

    return create_workflow_and_run


def create_design_workflow_tool(
    model,
    session_id: str,
    system_prompt: str,
    callbacks: list | None = None,
    turn_id: str | None = None,
) -> callable:
    @tool
    async def workflow_agent(goal: str) -> dict:
        """
        Workflow planner and executor.
        Use this for tasks that need workflow planning and execution.
        Returns structured execution metadata and may include a ready-to-send final_answer.
        """
        db = SessionLocal()
        try:
            session = _get_session(db, session_id)
            if not session:
                return {"status": "error", "error": "Session not found."}
            repair_state = _new_repair_state()
            workflow_agent_inst = WorkflowAgent(
                model=model,
                system_prompt=system_prompt,
                tools=[
                    create_workflow_and_run_tool(session_id, turn_id=turn_id, repair_state=repair_state),
                    create_read_workflow_tool(session_id),
                    create_update_workflow_tool(
                        session_id,
                        str(session.user_id),
                        turn_id=turn_id,
                        repair_state=repair_state,
                    ),
                    create_run_workflow_tool(session_id, turn_id=turn_id, repair_state=repair_state),
                ],
                max_steps=24,
                stop_condition=lambda: repair_state.get("terminal_failure"),
            )
            result = await workflow_agent_inst.ainvoke(
                goal,
                thread_id=f"workflow_agent_{session_id}",
                config={"callbacks": callbacks},
            )
            terminal_failure = repair_state.get("terminal_failure")
            try:
                snapshot = (
                    build_workspace_state_for_turn(db, turn_id)
                    if turn_id
                    else build_workspace_state(db, session_id)
                )
            except Exception as exc:
                logger.warning("[workflow_agent tool] failed to build workspace state: %s", exc)
                snapshot = None
            serialized = _serialize_workspace_state(snapshot) if snapshot else {}
            run = serialized.get("run") or {}
            run_result = run.get("result") or {}
            run_status = run.get("status") or "pending"
            final_answer = _extract_final_answer(serialized)
            if terminal_failure:
                return {
                    "status": "failed",
                    "next_action": "reply_directly",
                    "turn_id": turn_id,
                    "draft_id": terminal_failure.get("draft_id") or (serialized.get("draft") or {}).get("id"),
                    "run_id": terminal_failure.get("run_id") or run.get("id"),
                    "run_status": "failed",
                    "error": terminal_failure.get("error"),
                    "error_type": terminal_failure.get("error_type"),
                    "error_summary": terminal_failure.get("error_summary"),
                    "issues": terminal_failure.get("issues") or [],
                    "validation_errors": terminal_failure.get("validation_errors"),
                    "details": terminal_failure.get("details"),
                    "artifacts": [artifact.get("kind") for artifact in serialized.get("artifacts", [])],
                    "workspace_state": serialized,
                    "final_answer": _terminal_failure_reply(goal, terminal_failure),
                    "message_count": len(result.get("messages", [])),
                }
            return {
                "status": "success" if run_status == "success" else run_status,
                "next_action": "reply_directly" if final_answer and run_status == "success" else "summarize_workflow_result",
                "turn_id": turn_id,
                "draft_id": (serialized.get("draft") or {}).get("id"),
                "run_id": run.get("id"),
                "run_status": run_status,
                "error": run.get("error"),
                "validation_errors": run_result.get("validation_errors"),
                "details": run_result.get("details"),
                "artifacts": [artifact.get("kind") for artifact in serialized.get("artifacts", [])],
                "workspace_state": serialized,
                "final_answer": final_answer,
                "message_count": len(result.get("messages", [])),
            }
        finally:
            db.close()

    return workflow_agent


def create_summarize_workflow_result_tool(
    model,
    session_id: str,
    turn_id: str | None = None,
) -> callable:
    @tool
    async def summarize_workflow_result(question: str) -> str:
        """
        Summarize the latest workflow run for the current user request.
        Always use this after workflow_agent before replying to the user.
        """
        db = SessionLocal()
        try:
            snapshot = (
                build_workspace_state_for_turn(db, turn_id)
                if turn_id
                else build_workspace_state(db, session_id)
            )
        finally:
            db.close()

        serialized = _serialize_workspace_state(snapshot)
        run = serialized.get("run")
        if not run:
            return "No workflow run is available to summarize yet."
        final_answer = _extract_final_answer(serialized)
        if final_answer:
            return final_answer

        prompt = build_workflow_summary_prompt(question, serialized)
        response = await model.ainvoke(
            [
                SystemMessage(content=prompt),
                HumanMessage(content=question),
            ]
        )
        content = getattr(response, "content", "")
        return content if isinstance(content, str) else str(content)

    return summarize_workflow_result
