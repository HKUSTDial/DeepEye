import os
import asyncio
import uuid
from typing import Dict, Any

from deepeye.workflows.registry import NodeSpec
from app.node.base import BaseNode
from deepeye.workflows.engine import NodeHandler

# 假设我们将你的核心逻辑文件放置在 app.services 下
# 如果路径不同，请根据实际情况修改 import
from analysis_pipline import AutoReportPipeline


class AnalysisReportGenerator(BaseNode):
    node_type = "analysis.report_generator"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="Generate a comprehensive HTML data analysis report from CSV based on user query.",
            inputs={
                "csv_path": {
                    "schema": "string",
                    "required": True,
                    "description": "Path to the input CSV file"
                },
                "query": {
                    "schema": "string",
                    "required": True,
                    "description": "Analytical goal or question"
                }
            },
            outputs={
                "report_path": {
                    "schema": "string",
                    "description": "Path to the generated HTML report"
                }
            },
            params_schema={
                "api_key": {
                    "type": "string",
                    "required": False,
                    "secret": True,
                    "description": "LLM API Key (optional if set in env)"
                },
                "base_url": {
                    "type": "string",
                    "required": False,
                    "description": "LLM Base URL (optional if set in env)"
                }
            },
        )

    @classmethod
    def build_handler(cls, db, user_id, sandbox=None) -> NodeHandler | None:
        async def handler(inputs: Dict[str, Any], params: Dict[str, Any], context: Any):
            # 1. 准备配置：优先使用 Params，其次使用环境变量
            api_key = params.get("api_key") or os.getenv("OPENAI_API_KEY")
            base_url = params.get("base_url") or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

            if not api_key:
                raise ValueError("API Key is required for Analysis Report Generator.")

            # 2. 获取输入
            csv_path = inputs.get("csv_path")
            user_query = inputs.get("query")

            if not csv_path or not os.path.exists(csv_path):
                raise FileNotFoundError(f"Input CSV file not found: {csv_path}")

            # 3. 确定输出路径
            # 使用 sandbox 路径（如果提供），否则使用 /workspace
            # 生成唯一文件名以避免冲突
            filename = f"analysis_report_{uuid.uuid4().hex[:8]}.html"
            workspace_dir = "/workspace"  # 或从 sandbox 获取路径

            # 如果 sandbox 对象有获取路径的方法，建议使用它
            # 例如: output_path = sandbox.get_path(filename)
            # 这里为了通用性，假设绝对路径
            output_path = os.path.join(workspace_dir, filename)

            # 4. 初始化 Pipeline
            # 注意：这里实例化你的 AutoReportPipeline 类
            pipeline = AutoReportPipeline(api_key=api_key, base_url=base_url)

            # 5. 执行生成逻辑
            # 由于 pipeline.run 是同步阻塞代码，使用 to_thread 在线程池中运行
            # 这样不会阻塞外层的 Async 框架
            await asyncio.to_thread(
                pipeline.run,
                csv_path=csv_path,
                user_query=user_query,
                output_html_path=output_path
            )

            # 6. 返回结果
            return {"report_path": output_path}

        return handler