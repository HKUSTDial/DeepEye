from __future__ import annotations

import json
import os
import logging
import traceback
import io
import tarfile
import shutil
import asyncio
        
from typing import Any, Dict, List
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

try:
    import pandas as pd
except ImportError:
    pd = None

from app.node.core.base import BaseNode
from app.repositories import DataSourceRepository
from deepeye.workflows.registry import NodeSpec
from deepeye.workflows.models import Port
from app.node.dashboard.nl2dashboard.design import DashboardDesigner
from app.node.dashboard.nl2dashboard.engineering import DashboardEngineer
from app.node.dashboard.nl2dashboard.llm_compat import LLMClient
from app.core.config import settings
from app.services.workflow_events import build_workflow_artifact, publish_workflow_event_sync

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
        import threading
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
            except:
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
            except:
                pass

        if sync:
            _sync_publish()
        else:
            threading.Thread(target=_sync_publish, daemon=True).start()

    def _get_datasource_schema(self, datasource_id: str) -> List[Dict[str, Any]]:
        try:
            ds = DataSourceRepository(self.db).get(datasource_id)
            if not ds: return []
            connection_string = ds.connection_string
            if not any(connection_string.startswith(p) for p in ["postgresql://", "mysql://", "sqlite://"]):
                return []
            data_engine = create_engine(connection_string)
            inspector = inspect(data_engine)
            tables = inspector.get_table_names()[:10]
            items = []
            for name in tables:
                columns = inspector.get_columns(name)[:20]
                items.append({
                    "name": name,
                    "kind": "table",
                    "columns": [{"name": col.get("name"), "type": str(col.get("type"))} for col in columns]
                })
            return items
        except Exception as e:
            logger.warning(f"Failed to fetch schema for datasource {datasource_id}: {e}")
            return []

    def _ensure_sandbox(self):
        """Ensure sandbox reference is up-to-date and available"""
        if not self.sandbox:
            return False
            
        try:
            if self.sandbox.container:
                self.sandbox.container.reload()
                if self.sandbox.container.status == "running":
                    return True
                else:
                    self.sandbox.container.start()
                    return True
        except Exception:
            pass
            
        # Try to refresh (rediscover container via session_id)
        if getattr(self.sandbox, 'session_id', None):
            try:
                from app.sandbox.manager import sandbox_manager
                import asyncio
                import threading
                from concurrent.futures import Future
                
                # Always run async logic in separate thread to avoid loop conflicts
                def _get_sb_thread(f, sid):
                    try:
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        res = new_loop.run_until_complete(sandbox_manager.get_or_create_sandbox(sid))
                        f.set_result(res)
                        new_loop.close()
                    except Exception as te:
                        f.set_exception(te)
                
                fut = Future()
                t = threading.Thread(target=_get_sb_thread, args=(fut, self.sandbox.session_id))
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
        question = inputs.get("question") or params.get("question")
        datasource_id = inputs.get("datasource_id") or params.get("datasource_id")
        
        # 1. Path logic alignment with PythonCodeHandler
        safe_id = "".join(ch if str(ch).isalnum() or ch in ("-", "_") else "_" for ch in str(node.id)) or "dashboard"
        sandbox_base = "/workspace/.workflow_scripts"
        
        # 2. Unified input data handling
        data_input = inputs.get("data") or params.get("data")
        dataset_path = None
        
        # Temporary local path (using Beijing timestamp for fresh directory)
        # Server defaults to UTC, force +8 hours
        import time
        bj_time = time.gmtime(time.time() + 8 * 3600)
        run_ts = time.strftime('%Y%m%d_%H%M%S', bj_time)
        local_tmp_dir = f"/tmp/deepeye_{safe_id}_{run_ts}"
        os.makedirs(local_tmp_dir, exist_ok=True)

        try:
            if data_input:
                # Try to parse dict/list potentially serialized as string
                print(f"[DEBUG] Attempting to parse data input: {data_input}")
                if isinstance(data_input, str) and data_input.strip().startswith(("{", "[")):
                    try:
                        import ast
                        # Use ast.literal_eval over json.loads for Python repr format
                        parsed = ast.literal_eval(data_input.strip())
                        if isinstance(parsed, (dict, list)):
                            data_input = parsed
                            print(f"[DEBUG] Successfully parsed string input as {data_input}")
                    except Exception:
                        # If parsing fails, treat as normal string path
                        pass

                if isinstance(data_input, list):
                    if not data_input:
                        print("[WARN] Received empty list for data_input")
                    # Save a local CSV for analysis
                    local_csv = os.path.join(local_tmp_dir, f"{safe_id}_input.csv")
                    df = pd.DataFrame(data_input)
                    if df.empty and not df.columns.tolist():
                        # Create placeholder column to prevent pandas read_csv error
                        df = pd.DataFrame(columns=["empty_data"])
                    df.to_csv(local_csv, index=False)
                    dataset_path = local_csv
                    
                    # Sync to sandbox for user visibility
                    if self.sandbox:
                        csv_content = df.to_csv(index=False)
                        self._write_to_sandbox(f"{sandbox_base}/{safe_id}_input.csv", csv_content)
                        print(f"[DEBUG] Data synced to sandbox: {sandbox_base}/{safe_id}_input.csv")
                
                elif isinstance(data_input, dict):
                    # Strategy: Convert nested dict to Long Format to avoid NaN issues in Wide Format
                    print(f"[DEBUG] Dict input detected, converting to Long Format...")
                    
                    rows = []
                    for main_key, sub_content in data_input.items():
                        if isinstance(sub_content, dict):
                            # Handle nested dict: {"monthly_revenue": {"2025-08": 6580.0, ...}}
                            for sub_key, sub_val in sub_content.items():
                                rows.append({
                                    "dimension": main_key,
                                    "name": str(sub_key),
                                    "value": sub_val
                                })
                        elif isinstance(sub_content, (list, tuple)) and not isinstance(sub_content, str):
                            # Handle list: {"tags": ["a", "b"]}
                            for item in sub_content:
                                rows.append({
                                    "dimension": main_key,
                                    "name": str(item),
                                    "value": 1 # Count mode
                                })
                        else:
                            # Handle simple K-V: {"total": 100}
                            rows.append({
                                "dimension": "summary",
                                "name": str(main_key),
                                "value": sub_content
                            })
                    
                    df = pd.DataFrame(rows)
                    
                    # Key fix: Keep original field names in CSV for LLM generated Filter matching
                    # app.py handles logic: if field == dimension, filter name
                    
                    if df.empty:
                        df = pd.DataFrame(columns=["dimension", "name", "value"])
                    
                    local_csv = os.path.join(local_tmp_dir, f"{safe_id}_input.csv")
                    df.to_csv(local_csv, index=False)
                    dataset_path = local_csv
                    
                    if self.sandbox:
                        csv_content = df.to_csv(index=False)
                        self._write_to_sandbox(f"{sandbox_base}/{safe_id}_input.csv", csv_content)
                        print(f"[DEBUG] Long Format data synced to sandbox: {sandbox_base}/{safe_id}_input.csv")

                elif isinstance(data_input, str):
                    # If sandbox path (starts with /workspace), try reading from sandbox to local
                    if data_input.startswith("/workspace"):
                        print(f"[DEBUG] Reading data from sandbox: {data_input}")
                        res = self.sandbox.container.exec_run(f"cat {data_input}")
                        if res.exit_code == 0:
                            local_csv = os.path.join(local_tmp_dir, "input_from_sandbox.csv")
                            with open(local_csv, "wb") as f:
                                f.write(res.output)
                            dataset_path = local_csv
                        else:
                            dataset_path = data_input # fallback
                    else:
                        dataset_path = data_input
        except Exception as e:
            print(f"[ERROR] Data transportation failed: {e}")

        # 3. Determine local output path
        local_output_path = os.path.join(local_tmp_dir, "output")
        os.makedirs(local_output_path, exist_ok=True)

        # 4. Run core logic (completed in backend container)
        try:
            print(f"[DEBUG] Analyzing data | Question: {question}")
            # self._emit_log(msg)
            
            data_schema = inputs.get("data_schema") or params.get("data_schema")
            if not data_schema and datasource_id:
                data_schema = self._get_datasource_schema(datasource_id)

            api_key = settings.LLM_API_KEY
            base_url = settings.LLM_BASE_URL
            
            # Priority: node params > system config model
            model = params.get("model")
            if not model or model == "default":
                model = settings.LLM_MODEL
                
            print(f"[DEBUG] Using model: {model}")
            
            # Default question if empty
            if not question:
                question = "Analyze and present key information from the data"
                print(f"[DEBUG] Question is empty, using default value: {question}")
            
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
                print(f"[*] Moving generation results to sandbox workspace...")
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
                    print(f"[ERROR] No valid sandbox container available for put_archive")
                
                final_sandbox_path = f"{sandbox_base}/{sandbox_folder_name}"
                print(f"[✓] Synchronization successful, sandbox path: {final_sandbox_path}")
                self._emit_log(f"Generation results successfully synchronized to the files: `{sandbox_folder_name}`\n")
            else:
                final_sandbox_path = va_app_path

            # --- Auto-deploy to independent container and provide access link ---
            va_source_path = os.path.join(local_output_path, "va_app")
            
            # URL preset, must match container naming rules in DashboardDeployService
            full_url = f"/dashboards/deepeye-nl2dashboard-{safe_id}/"
            
            if os.path.exists(va_source_path):
                try:
                    # 1. Local import to cut cyclic dependency
                    
                    print(f"[*] Starting independent dashboard service container (ID: {safe_id})...")
                    
                    # 2. Asynchronous trigger: use thread for background deployment
                    import threading
                    def _do_deploy():
                        # Create independent event loop for new thread
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            # Local import and execute
                            from app.services.dashboard_deploy_service import dashboard_deployer
                            new_loop.run_until_complete(dashboard_deployer.deploy(safe_id, va_source_path))
                            
                            # Sequential send in sync mode to prevent frontend conflicts
                            self._emit_log("Dashboard deployment complete!\n", sync=True)
                            print(f"Dashboard deployment complete! Access it here: {full_url}\n")
                            self._emit_workflow_event(
                                "artifact_refresh",
                                {
                                    "artifact": build_workflow_artifact(
                                        "dashboard",
                                        dashboard_url=full_url,
                                        output_path=final_sandbox_path,
                                    ),
                                },
                                sync=True,
                            )
                        except Exception as e:
                            print(f"[ERROR] Background deployment failed: {e}")
                            self._emit_log(f"Dashboard deployment failed: {e}")
                        finally:
                            new_loop.close()
                            # Cleanup local temporary directory after deployment
                            try:
                                if os.path.exists(local_tmp_dir):
                                    shutil.rmtree(local_tmp_dir)
                                    print(f"[DEBUG] Cleaned up local temporary directory: {local_tmp_dir}")
                            except Exception as ce:
                                print(f"[WARN] Failed to cleanup local directory {local_tmp_dir}: {ce}")

                    threading.Thread(target=_do_deploy, daemon=True).start()
                    
                    print(f"\n" + "-"*20)
                    print(f"[SUCCESS] Dashboard deployment task submitted: {full_url}")
                    print(f"-"*20 + "\n")
                except Exception as de:
                    print(f"[WARN] Failed to submit deployment task: {de}")
                    traceback.print_exc()

            self._emit_workflow_event(
                "artifact_ready",
                {
                    "artifact": build_workflow_artifact(
                        "dashboard",
                        dashboard_url=full_url,
                        output_path=final_sandbox_path,
                    ),
                },
                sync=True,
            )
            return {
                "output_path": final_sandbox_path,
                "dashboard_url": full_url,
                "dashboard_config": design_result
            }
        except Exception as e:
            traceback.print_exc()
            raise RuntimeError(f"Execution failed: {e}")

class NL2DashboardNode(BaseNode):
    node_type = "data.generate_dashboard"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="Generate a full interactive dashboard from natural language.",
            inputs={
                "question": Port(schema="string", description="User query"),
                "data": Port(schema="any", required=False, description="Data records or sandbox path"),
            },
            outputs={
                "output_path": Port(schema="string", description="Path in sandbox"),
                "dashboard_config": Port(schema="dict"),
                "dashboard_url": Port(schema="string", description="The URL to access the generated dashboard"),
            },
            params_schema={
                "model": {"type": "string", "default": settings.LLM_MODEL, "required": False},
                "data": {"type": "any", "required": False},
                "datasource_id": {"type": "string", "required": False},
                "data_schema": {"type": "any", "required": False},
            },
        )

    @classmethod
    def build_handler(cls, db: Session, user_id: str, sandbox=None):
        return NL2DashboardHandler(db, user_id, sandbox)
