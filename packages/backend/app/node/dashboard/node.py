from __future__ import annotations

import json
import os
import logging
import traceback
import io
import tarfile
import shutil
import asyncio
import threading
from pathlib import Path
        
from typing import Any, Dict, List
from sqlalchemy.orm import Session

try:
    import pandas as pd
except ImportError:
    pd = None

from app.node.core.base import BaseNode
from app.workflow.services.datasets import dataset_ref_columns, dataset_ref_preview, download_dataset_ref_to_local_csv, is_dataset_ref
from deepeye.workflows.registry import NodeSpec
from deepeye.workflows.models import Port
from app.node.dashboard.nl2dashboard.design import DashboardDesigner
from app.node.dashboard.nl2dashboard.engineering import DashboardEngineer
from app.node.dashboard.nl2dashboard.llm_compat import LLMClient
from app.core.config import settings
from app.workflow.events import build_workflow_artifact, publish_workflow_event_sync

logger = logging.getLogger(__name__)

class NL2DashboardHandler:
    def __init__(self, db: Session, user_id: str, sandbox=None):
        self.db = db
        self.user_id = user_id
        self.sandbox = sandbox # DockerSandbox instance

    def _emit_log(self, text: str, sync: bool = False):
        """Sync logs to frontend SSE dialog"""
        if not self.sandbox or not getattr(self.sandbox, "session_id", None):
            return
        
        # Core: Use independent thread to execute immediately
        from app.infra import RedisEventBus
        from app.schemas import AgentEvent, AgentEventType
        from app.core.config import settings

        def _sync_publish():
            # Create a temporary event loop in new thread for Redis publishing
            try:
                temp_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(temp_loop)
                
                async def _task():
                    bus = RedisEventBus(settings.REDIS_URL)
                    event = AgentEvent(
                        type=AgentEventType.TOKEN,
                        source="supervisor",
                        content=f"\n> **Dashboard Generation**: {text}\n"
                    )
                    # Publish immediately
                    await bus.publish(f"session:{self.sandbox.session_id}", event.model_dump_json())
                    await bus.close()
                
                temp_loop.run_until_complete(_task())
                temp_loop.close()
            except Exception:
                pass

        if sync:
            _sync_publish()
        else:
            # Start daemon thread to ensure non-blocking but message delivery
            threading.Thread(target=_sync_publish, daemon=True).start()

    def _emit_workflow_event(self, phase: str, payload: Dict[str, Any] = None, sync: bool = False):
        """Send workflow events to frontend"""
        if not self.sandbox or not getattr(self.sandbox, "session_id", None):
            return

        def _sync_publish():
            try:
                publish_workflow_event_sync(
                    f"session:{self.sandbox.session_id}",
                    self.sandbox.session_id,
                    phase,
                    payload or {},
                )
            except Exception:
                pass

        if sync:
            _sync_publish()
        else:
            threading.Thread(target=_sync_publish, daemon=True).start()

    def _infer_dataset_schema(self, dataset_ref: dict[str, Any] | None) -> List[Dict[str, Any]]:
        if not is_dataset_ref(dataset_ref):
            return []
        columns = dataset_ref_columns(dataset_ref)
        preview = dataset_ref_preview(dataset_ref, limit=5)
        type_by_column: Dict[str, str] = {}
        for column in columns:
            inferred = "unknown"
            for row in preview:
                value = row.get(column)
                if value is None:
                    continue
                inferred = type(value).__name__
                break
            type_by_column[column] = inferred
        return [
            {
                "name": Path(str(dataset_ref.get("path") or "dataset")).stem,
                "kind": "dataset",
                "columns": [{"name": column, "type": type_by_column.get(column, "unknown")} for column in columns],
            }
        ]

    def _ensure_sandbox(self):
        """Ensure sandbox reference is up-to-date and available"""
        if not self.sandbox:
            return False

        container = getattr(self.sandbox, "container", None)
        if container is not None:
            try:
                reload_container = getattr(container, "reload", None)
                if callable(reload_container):
                    reload_container()

                status = getattr(container, "status", None)
                if status == "running":
                    return True
                if status is None and callable(getattr(container, "exec_run", None)):
                    return True

                start_container = getattr(container, "start", None)
                if callable(start_container):
                    start_container()
                    return True
            except Exception:
                pass

        try:
            session_id = getattr(self.sandbox, 'session_id', None)
            if not session_id:
                return False

            from app.sandbox.manager import sandbox_manager
            from concurrent.futures import Future

            # Always run async refresh logic in a daemon thread to avoid loop conflicts.
            def _get_sb_thread(f, sid):
                new_loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(new_loop)
                    res = new_loop.run_until_complete(sandbox_manager.get_or_create_sandbox(sid))
                    f.set_result(res)
                except Exception as te:
                    f.set_exception(te)
                finally:
                    asyncio.set_event_loop(None)
                    new_loop.close()

            fut = Future()
            t = threading.Thread(target=_get_sb_thread, args=(fut, session_id), daemon=True)
            t.start()
            self.sandbox = fut.result(timeout=30)

            print(f"[INFO] Sandbox refreshed: {self.sandbox.container_name}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to refresh sandbox: {e}")
            return False
        return False

    def _write_to_sandbox(self, path: str, content: str):
        """Write content to sandbox container"""
        if not self._ensure_sandbox():
            return
        
        # Ensure directory exists
        dir_name = os.path.dirname(path)
        self.sandbox.container.exec_run(f"mkdir -p {dir_name}")
        
        # Use tar stream for writing to avoid escaping issues
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            content_bytes = content.encode('utf-8')
            tarinfo = tarfile.TarInfo(name=os.path.basename(path))
            tarinfo.size = len(content_bytes)
            tar.addfile(tarinfo, io.BytesIO(content_bytes))
        
        tar_stream.seek(0)
        self.sandbox.container.put_archive(dir_name, tar_stream)

    def execute(self, node: Any, inputs: Dict[str, Any], context: Any) -> Dict[str, Any]:
        print("\n" + "="*30 + " NL2DASHBOARD (SANDBOX MODE) " + "="*30)
        params = node.params
        question = params.get("question")
        if not question:
            raise ValueError("question is required")
        
        # 1. Path logic alignment with PythonCodeHandler
        safe_id = "".join(ch if str(ch).isalnum() or ch in ("-", "_") else "_" for ch in str(node.id)) or "dashboard"
        sandbox_base = "/workspace/.workflow_scripts"
        
        # 2. Unified input data handling
        dataset_ref = inputs.get("dataset_ref")
        dataset_path = None
        
        # Temporary local path (using Beijing timestamp for fresh directory)
        # Server defaults to UTC, force +8 hours
        import time
        bj_time = time.gmtime(time.time() + 8 * 3600)
        run_ts = time.strftime('%Y%m%d_%H%M%S', bj_time)
        local_tmp_dir = f"/tmp/deepeye_{safe_id}_{run_ts}"
        os.makedirs(local_tmp_dir, exist_ok=True)

        try:
            if is_dataset_ref(dataset_ref):
                dataset_path = download_dataset_ref_to_local_csv(
                    dataset_ref,
                    sandbox=self.sandbox,
                    tmp_dir=local_tmp_dir,
                    name_hint=f"{safe_id}_input",
                )
        except Exception as e:
            print(f"[ERROR] Data transportation failed: {e}")
            raise RuntimeError(f"Failed to prepare dashboard dataset: {e}") from e

        if not dataset_path:
            raise ValueError("dataset_ref input is required")

        # 3. Determine local output path
        local_output_path = os.path.join(local_tmp_dir, "output")
        os.makedirs(local_output_path, exist_ok=True)

        # 4. Run core logic (completed in backend container)
        try:
            print(f"[DEBUG] Analyzing data | Question: {question}")
            # self._emit_log(msg)
            
            data_schema = self._infer_dataset_schema(dataset_ref)

            api_key = settings.LLM_API_KEY
            base_url = settings.LLM_BASE_URL
            
            model = settings.LLM_MODEL
                
            print(f"[DEBUG] Using model: {model}")
            
            llm_client = LLMClient(api_key=api_key, base_url=base_url)
            
            info_doc = {
                "question": question,
                "dataset_path": dataset_path,
                "output_path": local_output_path,
                "data_schema": data_schema
            }
            
            # --- Debug Output: Verify input data and schema ---
            print(f"\n{'='*20} NL2DASHBOARD INPUT DEBUG {'='*20}")
            print(f"Question: {question}")
            print(f"Dataset Path: {dataset_path}")
            if dataset_path and os.path.exists(dataset_path):
                try:
                    df_preview = pd.read_csv(dataset_path, nrows=5)
                    print(f"Data Preview (5 rows):\n{df_preview.to_string()}")
                    print(f"Columns: {list(df_preview.columns)}")
                except Exception as de:
                    print(f"Error reading data preview: {de}")
            else:
                print("Dataset path does not exist or is empty")
            
            print(f"Data Schema: {json.dumps(data_schema, indent=2) if data_schema else 'None'}")
            print(f"{'='*60}\n")
            # --------------------------------------------

            # self._emit_log("Designing dashboard structure and generating visualizations...")
            designer = DashboardDesigner(llm_client=llm_client, model=model)
            design_result = designer.design(
                info_doc=info_doc, 
                output_dir=local_output_path,
                callback=self._emit_log
            )
            
            self._emit_log("Implementing engineering features and filter binding...")
            engineer = DashboardEngineer(llm_client=llm_client, model=model)
            va_app_path = engineer.implement(
                design_result=design_result,
                output_path=local_output_path,
                info_doc=info_doc
            )
            
            # 5. Sync entire results folder to sandbox
            if self.sandbox:
                print("[*] Moving generation results to sandbox workspace...")
                # self._emit_log("Synchronizing results to the sandbox workspace...")
                # Compress local directory
                tar_stream = io.BytesIO()
                # Folder name includes timestamp for uniqueness
                sandbox_folder_name = f"dashboard_{run_ts}"
                with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                    tar.add(local_output_path, arcname=sandbox_folder_name)
                tar_stream.seek(0)
                # Put in sandbox
                self._ensure_sandbox()

                if self.sandbox and self.sandbox.container:
                    self.sandbox.container.exec_run(f"mkdir -p {sandbox_base}")
                    self.sandbox.container.put_archive(sandbox_base, tar_stream)
                else:
                    print("[ERROR] No valid sandbox container available for put_archive")
                
                final_sandbox_path = f"{sandbox_base}/{sandbox_folder_name}"
                print(f"[✓] Synchronization successful, sandbox path: {final_sandbox_path}")
                self._emit_log(f"Generation results successfully synchronized to the files: `{sandbox_folder_name}`\n")
            else:
                final_sandbox_path = va_app_path

            # --- Deploy preview synchronously so workflow status matches real deploy outcome ---
            va_source_path = os.path.join(local_output_path, "va_app")
            if not os.path.exists(va_source_path):
                raise FileNotFoundError(f"Generated dashboard app not found: {va_source_path}")

            print(f"[*] Starting independent dashboard service container (ID: {safe_id})...")
            from app.deploy.services.dashboard import dashboard_deployer

            deploy_loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(deploy_loop)
                deploy_result = deploy_loop.run_until_complete(
                    dashboard_deployer.deploy(
                        safe_id,
                        va_source_path,
                        session_id=getattr(self.sandbox, "session_id", None),
                    )
                )
            finally:
                asyncio.set_event_loop(None)
                deploy_loop.close()

            dashboard_url = str(deploy_result.get("url") or f"/dashboards/deepeye-nl2dashboard-{safe_id}/")
            deploy_status = str(deploy_result.get("status") or "")
            if deploy_status != "running":
                raise RuntimeError(
                    f"Dashboard deployment returned non-running status: {deploy_status or 'unknown'}"
                )

            self._emit_log("Dashboard deployment complete!\n", sync=True)
            print(f"Dashboard deployment complete! Access it here: {dashboard_url}\n")
            self._emit_workflow_event(
                "artifact_ready",
                {
                    "artifact": build_workflow_artifact(
                        "dashboard",
                        node_id=str(node.id),
                        dashboard_url=dashboard_url,
                        output_path=final_sandbox_path,
                    ),
                },
                sync=True,
            )
            return {
                "output_path": final_sandbox_path,
                "dashboard_url": dashboard_url,
            }
        except Exception as e:
            self._emit_log(f"Dashboard generation failed: {e}", sync=True)
            self._emit_workflow_event(
                "artifact_failed",
                {
                    "artifact": build_workflow_artifact(
                        "dashboard",
                        node_id=str(node.id),
                        output_path=locals().get("final_sandbox_path"),
                        dashboard_url=locals().get("dashboard_url"),
                    ),
                    "error": str(e),
                    "message": f"Dashboard generation failed: {e}",
                },
                sync=True,
            )
            traceback.print_exc()
            raise RuntimeError(f"Execution failed: {e}")
        finally:
            try:
                if os.path.exists(local_tmp_dir):
                    shutil.rmtree(local_tmp_dir)
                    print(f"[DEBUG] Cleaned up local temporary directory: {local_tmp_dir}")
            except Exception as cleanup_error:
                print(f"[WARN] Failed to cleanup local directory {local_tmp_dir}: {cleanup_error}")

class NL2DashboardNode(BaseNode):
    node_type = "data.generate_dashboard"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="Generate an interactive dashboard from a dataset and an analysis question.",
            inputs={
                "dataset_ref": Port(schema="dict", required=True, description="Dataset reference to visualize."),
            },
            outputs={
                "output_path": Port(schema="string", description="Sandbox path to the generated dashboard app."),
                "dashboard_url": Port(schema="string", description="URL for opening the generated dashboard."),
            },
            params_schema={
                "question": {"type": "string", "required": True, "description": "Dashboard request or analysis goal."},
            },
        )

    @classmethod
    def build_handler(cls, db: Session, user_id: str, sandbox=None):
        return NL2DashboardHandler(db, user_id, sandbox)
