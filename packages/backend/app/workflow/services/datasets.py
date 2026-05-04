from __future__ import annotations

import json
import os
import tarfile
import tempfile
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.infra.db import create_engine, json_safe_row
from app.repositories import DataSourceRepository
from app.datasource.services.specs import (
    get_datasource_filename,
    infer_file_type,
    normalize_datasource_type,
    sanitize_filename,
    workspace_data_path,
)

DATASET_DIR = "/workspace/.datasets"
DEFAULT_PREVIEW_LIMIT = 20
DEFAULT_TEXT_LIMIT = 4000


def build_dataset_ref(
    *,
    path: str,
    dataset_format: str,
    source: str,
    preview_rows: list[dict[str, Any]] | None = None,
    row_count: int | None = None,
    columns: list[str] | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "kind": "dataset_ref",
        "path": path,
        "format": dataset_format,
        "source": source,
    }
    if preview_rows:
        payload["preview_rows"] = preview_rows
    if row_count is not None:
        payload["row_count"] = row_count
    if columns:
        payload["columns"] = columns
    if name:
        payload["name"] = name
    return payload


def is_dataset_ref(value: Any) -> bool:
    return isinstance(value, dict) and value.get("kind") == "dataset_ref" and isinstance(value.get("path"), str)


def dataset_ref_preview(dataset_ref: dict[str, Any], limit: int = DEFAULT_PREVIEW_LIMIT) -> list[dict[str, Any]]:
    rows = dataset_ref.get("preview_rows")
    if not isinstance(rows, list):
        return []
    preview = [row for row in rows if isinstance(row, dict)]
    return preview[:limit]


def dataset_ref_path(dataset_ref: dict[str, Any]) -> str:
    path = dataset_ref.get("path")
    if not isinstance(path, str) or not path.strip():
        raise ValueError("dataset_ref.path is required")
    return path


def dataset_ref_format(dataset_ref: dict[str, Any]) -> str:
    raw = dataset_ref.get("format")
    if isinstance(raw, str) and raw.strip():
        return raw.strip().lower()
    return infer_file_type(dataset_ref_path(dataset_ref))


def dataset_ref_columns(dataset_ref: dict[str, Any]) -> list[str]:
    columns = dataset_ref.get("columns")
    if isinstance(columns, list):
        return [str(column) for column in columns if str(column).strip()]
    preview = dataset_ref_preview(dataset_ref)
    if preview:
        return sorted({key for row in preview for key in row})
    return []


def _truncate_text(value: str, limit: int = DEFAULT_TEXT_LIMIT) -> str:
    if len(value) <= limit:
        return value
    suffix = f"\n...[truncated {len(value) - limit} chars]"
    head = max(0, limit - len(suffix))
    return value[:head] + suffix


def compact_dataset_ref(
    dataset_ref: dict[str, Any],
    *,
    preview_limit: int = DEFAULT_PREVIEW_LIMIT,
) -> dict[str, Any]:
    compact = {
        "kind": "dataset_ref",
        "path": dataset_ref_path(dataset_ref),
        "format": dataset_ref_format(dataset_ref),
    }
    for key in ("source", "name", "row_count"):
        value = dataset_ref.get(key)
        if value not in (None, "", [], {}):
            compact[key] = value
    columns = dataset_ref_columns(dataset_ref)
    if columns:
        compact["columns"] = columns
    preview = dataset_ref_preview(dataset_ref, limit=preview_limit)
    if preview:
        compact["preview_rows"] = preview
    return compact


def compact_rows_preview(rows: list[dict[str, Any]] | None, limit: int = DEFAULT_PREVIEW_LIMIT) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    preview: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            preview.append(row)
        if len(preview) >= limit:
            break
    return preview


def compact_value_for_transport(
    value: Any,
    *,
    parent_key: str | None = None,
    row_limit: int = DEFAULT_PREVIEW_LIMIT,
    text_limit: int = DEFAULT_TEXT_LIMIT,
    list_limit: int = DEFAULT_PREVIEW_LIMIT,
) -> Any:
    if parent_key == "dataset_ref" and is_dataset_ref(value):
        return compact_dataset_ref(value, preview_limit=row_limit)
    if is_dataset_ref(value) and parent_key is None:
        return compact_dataset_ref(value, preview_limit=row_limit)

    if isinstance(value, dict):
        compact: dict[str, Any] = {}
        for key, item in value.items():
            if key in {"rows", "preview_rows"} and isinstance(item, list) and all(isinstance(row, dict) for row in item):
                preview = compact_rows_preview(item, limit=row_limit)
                compact[key] = preview
                if key == "rows":
                    compact.setdefault("preview_rows", preview)
                    compact.setdefault("row_count", len(item))
                    if preview:
                        compact.setdefault("columns", sorted({col for row in preview for col in row.keys()}))
                continue
            compact[key] = compact_value_for_transport(
                item,
                parent_key=key,
                row_limit=row_limit,
                text_limit=text_limit,
                list_limit=list_limit,
            )
        return compact

    if isinstance(value, list):
        compact_items = value[:list_limit]
        return [
            compact_value_for_transport(
                item,
                row_limit=row_limit,
                text_limit=text_limit,
                list_limit=list_limit,
            )
            for item in compact_items
        ]

    if isinstance(value, str):
        return _truncate_text(value, limit=text_limit)

    return value


def compact_node_outputs(
    outputs: dict[str, Any] | None,
    *,
    row_limit: int = DEFAULT_PREVIEW_LIMIT,
    text_limit: int = DEFAULT_TEXT_LIMIT,
) -> dict[str, Any] | None:
    if not isinstance(outputs, dict):
        return outputs
    compacted = compact_value_for_transport(
        outputs,
        row_limit=row_limit,
        text_limit=text_limit,
    )
    if isinstance(compacted, dict) and is_dataset_ref(compacted.get("dataset_ref")):
        for key in ("preview_rows", "row_count", "columns"):
            compacted.pop(key, None)
    return compacted


def compact_workflow_outputs(
    outputs: dict[str, Any] | None,
    *,
    row_limit: int = DEFAULT_PREVIEW_LIMIT,
    text_limit: int = DEFAULT_TEXT_LIMIT,
) -> dict[str, Any] | None:
    if not isinstance(outputs, dict):
        return outputs
    return {
        node_id: compact_node_outputs(node_outputs, row_limit=row_limit, text_limit=text_limit)
        if isinstance(node_outputs, dict)
        else compact_value_for_transport(node_outputs, row_limit=row_limit, text_limit=text_limit)
        for node_id, node_outputs in outputs.items()
    }


def compact_workflow_result(
    result: dict[str, Any] | None,
    *,
    row_limit: int = DEFAULT_PREVIEW_LIMIT,
    text_limit: int = DEFAULT_TEXT_LIMIT,
) -> dict[str, Any] | None:
    if not isinstance(result, dict):
        return result
    compact = dict(result)
    if isinstance(compact.get("outputs"), dict):
        compact["outputs"] = compact_workflow_outputs(
            compact["outputs"],
            row_limit=row_limit,
            text_limit=text_limit,
        )
    if isinstance(compact.get("artifacts"), list):
        compact["artifacts"] = compact_value_for_transport(
            compact["artifacts"],
            row_limit=row_limit,
            text_limit=text_limit,
        )
    for key in ("error", "message", "report_html"):
        if isinstance(compact.get(key), str):
            compact[key] = _truncate_text(compact[key], limit=text_limit)
    return compact


def upload_local_file_to_sandbox(sandbox, local_path: str, dest_path: str) -> None:
    if not sandbox or not getattr(sandbox, "container", None):
        raise RuntimeError("Sandbox not available for dataset upload")
    container = sandbox.container
    dest_dir = os.path.dirname(dest_path) or "/"
    exit_code, output = container.exec_run(cmd=["bash", "-c", f"mkdir -p {dest_dir}"], demux=True, workdir="/workspace")
    if exit_code != 0:
        stderr = output[1].decode("utf-8", errors="replace") if output and output[1] else ""
        raise RuntimeError(stderr or f"failed to create sandbox directory: {dest_dir}")

    tar_stream = tempfile.NamedTemporaryFile(suffix=".tar", delete=False)
    tar_path = tar_stream.name
    tar_stream.close()
    try:
        with tarfile.open(tar_path, mode="w") as tar:
            tar.add(local_path, arcname=os.path.basename(dest_path))
        with open(tar_path, "rb") as fp:
            container.put_archive(dest_dir, fp)
    finally:
        try:
            os.remove(tar_path)
        except FileNotFoundError:
            pass


def materialize_rows_to_sandbox_dataset(
    rows: list[dict[str, Any]],
    *,
    sandbox,
    name_hint: str,
    source: str,
    row_count: int | None = None,
    columns: list[str] | None = None,
    preview_limit: int = DEFAULT_PREVIEW_LIMIT,
) -> dict[str, Any]:
    safe_name = sanitize_filename(name_hint or "dataset")
    if not safe_name.endswith(".jsonl"):
        safe_name = f"{safe_name}.jsonl"
    dest_path = f"{DATASET_DIR}/{safe_name}"
    preview_rows = compact_rows_preview(rows, limit=preview_limit)
    resolved_columns = columns or sorted({key for row in rows for key in row.keys()})

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as tmp:
        tmp_path = tmp.name
        for row in rows:
            tmp.write(json.dumps(json_safe_row(dict(row)), ensure_ascii=False))
            tmp.write("\n")
    try:
        upload_local_file_to_sandbox(sandbox, tmp_path, dest_path)
    finally:
        try:
            os.remove(tmp_path)
        except FileNotFoundError:
            pass

    return build_dataset_ref(
        path=dest_path,
        dataset_format="jsonl",
        source=source,
        preview_rows=preview_rows,
        row_count=row_count if row_count is not None else len(rows),
        columns=resolved_columns,
        name=Path(dest_path).stem,
    )


def build_tabular_node_result(
    rows: list[dict[str, Any]],
    *,
    sandbox,
    source: str,
    name_hint: str,
    row_count: int | None = None,
    columns: list[str] | None = None,
    preview_limit: int = DEFAULT_PREVIEW_LIMIT,
) -> dict[str, Any]:
    resolved_columns = columns or sorted({key for row in rows for key in row.keys()})
    preview_rows = compact_rows_preview(rows, limit=preview_limit)
    resolved_row_count = row_count if row_count is not None else len(rows)
    result: dict[str, Any] = {}
    if sandbox:
        result["dataset_ref"] = materialize_rows_to_sandbox_dataset(
            rows,
            sandbox=sandbox,
            name_hint=name_hint,
            source=source,
            row_count=resolved_row_count,
            columns=resolved_columns,
            preview_limit=preview_limit,
        )
    else:
        result["dataset_ref"] = build_dataset_ref(
            path=f"/virtual/{sanitize_filename(name_hint or 'dataset')}.jsonl",
            dataset_format="jsonl",
            source=source,
            preview_rows=preview_rows,
            row_count=resolved_row_count,
            columns=resolved_columns,
            name=Path(name_hint or "dataset").stem,
        )
    return result


def materialize_sql_query_to_sandbox_dataset(
    *,
    db,
    user_id,
    sandbox,
    datasource_id: str | None,
    datasource_url: str | None,
    datasource_type: str | None,
    query: str,
    name_hint: str,
    source: str,
    preview_limit: int = DEFAULT_PREVIEW_LIMIT,
) -> dict[str, Any]:
    return materialize_sql_query_to_sandbox_result(
        db=db,
        user_id=user_id,
        sandbox=sandbox,
        datasource_id=datasource_id,
        datasource_url=datasource_url,
        datasource_type=datasource_type,
        query=query,
        name_hint=name_hint,
        source=source,
        preview_limit=preview_limit,
    )["dataset_ref"]


def materialize_sql_query_to_sandbox_result(
    *,
    db,
    user_id,
    sandbox,
    datasource_id: str | None,
    datasource_url: str | None,
    datasource_type: str | None,
    query: str,
    name_hint: str,
    source: str,
    preview_limit: int = DEFAULT_PREVIEW_LIMIT,
) -> dict[str, Any]:
    connection_string = datasource_url
    if datasource_id:
        ds = DataSourceRepository(db).get_by_id_and_user(datasource_id, user_id)
        if not ds:
            raise ValueError("datasource not found")
        connection_string = ds.connection_string
    if not connection_string:
        raise ValueError("datasource_url is required")

    engine = create_engine(connection_string)
    safe_name = sanitize_filename(name_hint or "query_result")
    if not safe_name.endswith(".jsonl"):
        safe_name = f"{safe_name}.jsonl"
    dest_path = f"{DATASET_DIR}/{safe_name}"
    preview_rows: list[dict[str, Any]] = []
    row_count = 0
    columns: list[str] = []

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as tmp:
        tmp_path = tmp.name
        with engine.connect() as conn:
            result = conn.execute(text(query))
            mappings = result.mappings()
            columns = list(result.keys())
            while True:
                batch = mappings.fetchmany(1000)
                if not batch:
                    break
                for row in batch:
                    item = json_safe_row(dict(row))
                    if len(preview_rows) < preview_limit:
                        preview_rows.append(item)
                    tmp.write(json.dumps(item, ensure_ascii=False))
                    tmp.write("\n")
                    row_count += 1
    try:
        upload_local_file_to_sandbox(sandbox, tmp_path, dest_path)
    finally:
        try:
            os.remove(tmp_path)
        except FileNotFoundError:
            pass

    dataset_ref = build_dataset_ref(
        path=dest_path,
        dataset_format="jsonl",
        source=source,
        preview_rows=preview_rows,
        row_count=row_count,
        columns=columns,
        name=Path(dest_path).stem,
    )
    return {"dataset_ref": dataset_ref}


def read_dataset_ref_rows(dataset_ref: dict[str, Any], *, sandbox, limit: int | None = None) -> list[dict[str, Any]]:
    path = dataset_ref_path(dataset_ref)
    dataset_format = dataset_ref_format(dataset_ref)
    if limit is not None and dataset_ref.get("preview_rows"):
        preview = dataset_ref_preview(dataset_ref, limit)
        if len(preview) >= limit:
            return preview
    if not sandbox or not getattr(sandbox, "container", None):
        raise RuntimeError("Sandbox not available for dataset_ref read")

    reader_script = r"""
import json
import sys
import pandas as pd

path = sys.argv[1]
fmt = sys.argv[2]
limit_raw = sys.argv[3]
limit = None if limit_raw == "__all__" else int(limit_raw)

if fmt == "jsonl":
    df = pd.read_json(path, lines=True)
elif fmt == "csv":
    df = pd.read_csv(path)
elif fmt in ("xlsx", "xls"):
    df = pd.read_excel(path)
elif fmt == "parquet":
    df = pd.read_parquet(path)
elif fmt == "json":
    try:
        df = pd.read_json(path, lines=True)
    except ValueError:
        df = pd.read_json(path)
else:
    raise ValueError(f"Unsupported dataset format: {fmt}")

if limit is not None:
    df = df.head(limit)
print(df.to_json(orient="records"))
"""
    raw_limit = "__all__" if limit is None else str(limit)
    result = sandbox.container.exec_run(
        cmd=["python3", "-c", reader_script, path, dataset_format, raw_limit],
        workdir="/workspace",
    )
    if result.exit_code != 0:
        err = (result.output or b"").decode("utf-8", errors="replace")
        raise RuntimeError(f"Failed to read dataset_ref rows: {err}")
    payload = (result.output or b"[]").decode("utf-8", errors="replace")
    rows = json.loads(payload)
    if not isinstance(rows, list):
        raise RuntimeError("dataset_ref read did not return a list")
    return [row for row in rows if isinstance(row, dict)]


def download_dataset_ref_to_local_csv(
    dataset_ref: dict[str, Any],
    *,
    sandbox,
    tmp_dir: str,
    name_hint: str | None = None,
) -> str:
    import pandas as pd

    if not sandbox or not getattr(sandbox, "container", None):
        raise RuntimeError("Sandbox not available for dataset_ref download")

    sandbox_path = dataset_ref_path(dataset_ref)
    dataset_format = dataset_ref_format(dataset_ref)
    exit_code, output = sandbox.container.exec_run(
        cmd=["cat", sandbox_path],
        demux=True,
        workdir="/workspace",
    )
    if exit_code != 0:
        stderr = output[1].decode("utf-8") if output and output[1] else ""
        raise RuntimeError(f"Failed to read dataset_ref file {sandbox_path}: {stderr}")

    content = output[0] if output and output[0] else b""
    stem = sanitize_filename(name_hint or dataset_ref.get("name") or Path(sandbox_path).stem or "dataset")
    local_input_path = os.path.join(tmp_dir, f"{stem}.{dataset_format}")
    with open(local_input_path, "wb") as fp:
        fp.write(content)

    if dataset_format == "csv":
        return local_input_path

    if dataset_format == "jsonl":
        df = pd.read_json(local_input_path, lines=True)
    elif dataset_format in ("json",):
        try:
            df = pd.read_json(local_input_path, lines=True)
        except ValueError:
            df = pd.read_json(local_input_path)
    elif dataset_format in ("xlsx", "xls"):
        df = pd.read_excel(local_input_path)
    elif dataset_format == "parquet":
        df = pd.read_parquet(local_input_path)
    else:
        raise ValueError(f"Unsupported dataset_ref format for CSV conversion: {dataset_format}")

    local_csv_path = os.path.join(tmp_dir, f"{stem}.csv")
    df.to_csv(local_csv_path, index=False)
    return local_csv_path


def dataset_ref_from_workspace_file(
    *,
    path: str,
    source: str,
    preview_rows: list[dict[str, Any]] | None = None,
    columns: list[str] | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    return build_dataset_ref(
        path=path,
        dataset_format=normalize_datasource_type(infer_file_type(path) or "csv"),
        source=source,
        preview_rows=preview_rows,
        columns=columns,
        name=name or Path(path).stem,
    )


def datasource_file_dataset_ref(*, datasource, preview_rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    filename = get_datasource_filename(getattr(datasource, "name", None), getattr(datasource, "storage_path", None))
    path = workspace_data_path(filename)
    columns = sorted({key for row in preview_rows or [] for key in row.keys()})
    return dataset_ref_from_workspace_file(
        path=path,
        source="datasource.read",
        preview_rows=preview_rows,
        columns=columns,
        name=Path(filename).stem,
    ) | ({"row_count": len(preview_rows)} if preview_rows is not None else {})
