from __future__ import annotations

import json
import os
import logging
import traceback
import io
import tarfile
import shutil
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
        
from typing import Any, Dict, List, Optional
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

try:
    import pandas as pd
except ImportError:
    pd = None

from app.node.base import BaseNode
from app.repositories import DataSourceRepository
from deepeye.workflows.registry import NodeSpec
from deepeye.workflows.models import Port
from .nl2dashboard.design import DashboardDesigner
from .nl2dashboard.engineering import DashboardEngineer
from .nl2dashboard.llm_compat import LLMClient
from app.core.config import settings

logger = logging.getLogger(__name__)

class NL2DashboardHandler:
    def __init__(self, db: Session, user_id: str, sandbox=None):
        self.db = db
        self.user_id = user_id
        self.sandbox = sandbox # 这是 DockerSandbox 实例

    def _emit_log(self, text: str, sync: bool = False):
        """将日志同步到前端 SSE 对话框"""
        if not self.sandbox or not getattr(self.sandbox, "session_id", None):
            return
        
        # 核心：使用独立线程立即执行，不等待主线程释放
        import threading
        from app.infra import RedisEventBus
        from app.schemas import AgentEvent, AgentEventType
        from app.core.config import settings

        def _sync_publish():
            # 在新线程中创建一个临时的事件循环来处理 Redis 发布
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
                    # 立即发布
                    await bus.publish(f"session:{self.sandbox.session_id}", event.model_dump_json())
                    await bus.close()
                
                temp_loop.run_until_complete(_task())
                temp_loop.close()
            except:
                pass

        if sync:
            _sync_publish()
        else:
            # 启动守护线程，确保不阻塞主流程，但也确保消息能发出去
            threading.Thread(target=_sync_publish, daemon=True).start()

    def _emit_workflow_event(self, phase: str, payload: Dict[str, Any] = None, sync: bool = False):
        """发送工作流事件到前端"""
        if not self.sandbox or not getattr(self.sandbox, "session_id", None):
            return
        
        import threading
        from app.infra import RedisEventBus
        from app.schemas import AgentEvent, AgentEventType
        from app.core.config import settings

        def _sync_publish():
            try:
                temp_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(temp_loop)
                
                async def _task():
                    bus = RedisEventBus(settings.REDIS_URL)
                    event = AgentEvent(
                        type=AgentEventType.WORKFLOW_EVENT,
                        source="workflow",
                        data={
                            "phase": phase,
                            "payload": payload or {}
                        }
                    )
                    await bus.publish(f"session:{self.sandbox.session_id}", event.model_dump_json())
                    await bus.close()
                
                temp_loop.run_until_complete(_task())
                temp_loop.close()
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
        """确保 sandbox 引用是最新且可用的"""
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
            
        # 尝试刷新 (通过 session_id 重新发现容器)
        if getattr(self.sandbox, 'session_id', None):
            try:
                from app.sandbox.manager import sandbox_manager
                import asyncio
                import threading
                from concurrent.futures import Future
                
                # 始终在独立线程中运行异步获取逻辑，避免与当前可能的 loop 冲突
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
        """将内容写入沙盒容器内部"""
        if not self._ensure_sandbox():
            return
        
        # 确保目录存在
        dir_name = os.path.dirname(path)
        self.sandbox.container.exec_run(f"mkdir -p {dir_name}")
        
        # 使用 tar 流式写入，避免转义问题（参考 docker-py 最佳实践）
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
        
        # 1. 路径逻辑对齐 PythonCodeHandler
        safe_id = "".join(ch if str(ch).isalnum() or ch in ("-", "_") else "_" for ch in str(node.id)) or "dashboard"
        sandbox_base = "/workspace/.workflow_scripts"
        
        # 2. 统一处理输入数据
        data_input = inputs.get("data") or params.get("data")
        dataset_path = None
        
        # 临时本地路径（使用北京时间戳确保目录新鲜，解决工作区显示旧时间的问题）
        # 服务器默认为 UTC，这里手动强制 +8 小时
        import time
        bj_time = time.gmtime(time.time() + 8 * 3600)
        run_ts = time.strftime('%Y%m%d_%H%M%S', bj_time)
        local_tmp_dir = f"/tmp/deepeye_{safe_id}_{run_ts}"
        os.makedirs(local_tmp_dir, exist_ok=True)

        try:
            if data_input:
                # 尝试解析可能被序列化为字符串的 dict/list (比如来自上游节点的输出)
                if isinstance(data_input, str) and data_input.strip().startswith(("{", "[")):
                    try:
                        import ast
                        # 使用 ast.literal_eval 比 json.loads 更能处理 Python repr 格式 (单引号、None等)
                        parsed = ast.literal_eval(data_input.strip())
                        if isinstance(parsed, (dict, list)):
                            data_input = parsed
                            print(f"[DEBUG] 成功将字符串输入解析为 {type(data_input)}")
                    except Exception as e:
                        # 如果解析失败，可能是正常的字符串路径，继续后续逻辑
                        pass

                if isinstance(data_input, list):
                    if not data_input:
                        print("[WARN] Received empty list for data_input")
                    # 在本地存一份 CSV 供分析使用
                    local_csv = os.path.join(local_tmp_dir, f"{safe_id}_input.csv")
                    df = pd.DataFrame(data_input)
                    if df.empty and not df.columns.tolist():
                        # 如果没有列，人为创建一个占位列防止 pandas read_csv 报错
                        df = pd.DataFrame(columns=["empty_data"])
                    df.to_csv(local_csv, index=False)
                    dataset_path = local_csv
                    
                    # 同时同步到沙盒一份，让用户可见
                    if self.sandbox:
                        csv_content = df.to_csv(index=False)
                        self._write_to_sandbox(f"{sandbox_base}/{safe_id}_input.csv", csv_content)
                        print(f"[DEBUG] 数据已同步到沙盒: {sandbox_base}/{safe_id}_input.csv")
                
                elif isinstance(data_input, dict):
                    # 如果是字典（可能是 Counter 结果），转换为长格式 DataFrame
                    print(f"[DEBUG] 检测到字典输入，尝试转换...")
                    rows = []
                    # 尝试处理简单的 k-v 字典或嵌套字典
                    for key, val in data_input.items():
                        if isinstance(val, dict) or (hasattr(val, 'items') and not isinstance(val, str)):
                            for sub_k, sub_v in val.items():
                                rows.append({"category": key, "name": sub_k, "value": sub_v})
                        else:
                            rows.append({"name": key, "value": val})
                    
                    local_csv = os.path.join(local_tmp_dir, f"{safe_id}_input.csv")
                    pd.DataFrame(rows).to_csv(local_csv, index=False)
                    dataset_path = local_csv
                    
                    if self.sandbox:
                        csv_content = pd.DataFrame(rows).to_csv(index=False)
                        self._write_to_sandbox(f"{sandbox_base}/{safe_id}_input.csv", csv_content)

                elif isinstance(data_input, str):
                    # 如果是沙盒路径（以 /workspace 开头），尝试从沙盒读取到本地
                    if data_input.startswith("/workspace"):
                        print(f"[DEBUG] 正在从沙盒读取数据: {data_input}")
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
            print(f"[ERROR] 数据搬运失败: {e}")

        # 3. 确定本地输出路径
        local_output_path = os.path.join(local_tmp_dir, "output")
        os.makedirs(local_output_path, exist_ok=True)

        # 4. 运行核心逻辑 (在 backend 容器完成)
        try:
            msg = f"Analyzing data for question: {question}"
            print(f"[DEBUG] Analyzing data | Question: {question}")
            # self._emit_log(msg)
            
            data_schema = inputs.get("data_schema") or params.get("data_schema")
            if not data_schema and datasource_id:
                data_schema = self._get_datasource_schema(datasource_id)

            api_key = settings.LLM_API_KEY
            base_url = settings.LLM_BASE_URL
            
            # 这里的逻辑：优先使用节点参数，如果没有或为 "default"，则使用配置中的模型，如果配置也是 "default"，则强制 gpt-4o
            model = params.get("model")
            if not model or model == "default":
                model = settings.LLM_MODEL
            if not model or model == "default":
                model = "gpt-4o"
                
            print(f"[DEBUG] Using model: {model}")
            
            # 如果 question 为空，给一个默认值防止报错
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
            
            # --- 新增调试输出：验证输入数据和 schema ---
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
            
            # 5. 关键一步：将生成的整个结果文件夹同步到沙盒
            if self.sandbox:
                print(f"[*] Moving generation results to sandbox workspace...")
                # self._emit_log("Synchronizing results to the sandbox workspace...")
                # 压缩本地目录
                tar_stream = io.BytesIO()
                # 文件夹名包含时间戳，确保用户在沙盒中看到的是最新创建的
                sandbox_folder_name = f"dashboard_{run_ts}"
                with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                    tar.add(local_output_path, arcname=sandbox_folder_name)
                tar_stream.seek(0)
                # 放入沙盒
                # 确保基础目录存在并引用有效
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

            # --- 新增：自动部署到独立容器并提供访问链接 ---
            # # va_app 的源代码路径通常在 local_output_path/va_app
            va_source_path = os.path.join(local_output_path, "va_app")
            # 通过当前文件的绝对路径来定位模板目录，这样在容器内外都能准确找到
            # current_dir = os.path.dirname(os.path.abspath(__file__))
            # va_source_path = os.path.join(current_dir, "nl2dashboard", "temp", "va_app")
            
            
            # 预设 URL，必须与 DashboardDeployService 中的容器名规则完全一致
            full_url = f"/dashboards/deepeye-nl2dashboard-{safe_id}/"
            deployment_info = {"url": full_url}
            
            if os.path.exists(va_source_path):
                try:
                    # 1. 局部导入，彻底切断启动时的循环引用
                    from app.services.dashboard_deploy_service import dashboard_deployer
                    
                    print(f"[*] Starting independent dashboard service container (ID: {safe_id})...")
                    # self._emit_log(f"Deploying the dashboard service in the background. It will be accessible via: {full_url}")
                    
                    # 2. 彻底异步触发：使用线程在后台执行部署，不阻塞当前同步流程 and 流式响应
                    import threading
                    def _do_deploy():
                        # 为新线程创建一个独立的事件循环
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            # 局部导入并执行
                            from app.services.dashboard_deploy_service import dashboard_deployer
                            new_loop.run_until_complete(dashboard_deployer.deploy(safe_id, va_source_path))
                            
                            # 使用同步模式顺序发送，并增加间隔防止前端处理冲突
                            self._emit_log("Dashboard deployment complete!\n", sync=True)
                            print(f"Dashboard deployment complete! Access it here: {full_url}\n")
                            self._emit_workflow_event("refresh", sync=True)
                        except Exception as e:
                            print(f"[ERROR] Background deployment failed: {e}")
                            self._emit_log(f"Dashboard deployment failed: {e}")
                        finally:
                            new_loop.close()
                            # 部署完成后清理本地临时目录，释放服务器空间
                            try:
                                if os.path.exists(local_tmp_dir):
                                    shutil.rmtree(local_tmp_dir)
                                    print(f"[DEBUG] Cleaned up local temporary directory: {local_tmp_dir}")
                            except Exception as ce:
                                print(f"[WARN] Failed to cleanup local directory {local_tmp_dir}: {ce}")

                    threading.Thread(target=_do_deploy, daemon=True).start()
                    
                    print(f"\n" + "-"*20)
                    print(f"[SUCCESS] Dashboard 部署任务已提交: {full_url}")
                    print(f"-"*20 + "\n")
                except Exception as de:
                    print(f"[WARN] 提交部署任务失败: {de}")
                    traceback.print_exc()

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
                "model": {"type": "string", "default": "gpt-4o", "required": False},
                "data": {"type": "any", "required": False},
                "datasource_id": {"type": "string", "required": False},
                "data_schema": {"type": "any", "required": False},
            },
        )

    @classmethod
    def build_handler(cls, db: Session, user_id: str, sandbox=None):
        return NL2DashboardHandler(db, user_id, sandbox)
