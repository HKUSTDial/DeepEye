"""NL2DV 节点实现 - 自然语言转数据视频配置

该节点接收自然语言描述和 DataFrame，通过 LLM 生成视频配置 JSON。
包含多智能体生成流程：数据分析 → 场景设计 → 动画编排。
"""

import os
from typing import Dict, Any, Optional, List
import pandas as pd

from deepeye.nodes.base import BaseNode, NodeConfig, NodeMetadata
from deepeye.nodes.io import (
    NodeInput,
    NodeOutput,
    NodeInputPort,
    NodeOutputPort,
    NodeInputSchema,
    NodeOutputSchema,
    NodeStatus,
)
from deepeye.llm import LLMClient
from .generator import SimpleConfigGenerator


class NL2DVConfig(NodeConfig):
    """NL2DV 节点配置"""
    
    # LLM 配置
    api_key: Optional[str] = None
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o"
    temperature: float = 0.7
    
    # 生成配置
    language: str = "English"  # English/Chinese
    skip_animations: bool = False  # 是否跳过动画生成
    
    # 视频元数据（可选，有默认值）
    fps: int = 30
    width: int = 1280
    height: int = 720
    
    # 调试
    verbose: bool = False


class NL2DVNode(BaseNode):
    """NL2DV 节点 - 自然语言转数据视频配置
    
    该节点接收自然语言描述和 DataFrame，通过 LLM 生成视频配置 JSON。
    包含多智能体生成流程：
    1. Data Analyst: 提取数据洞察
    2. Scene Designer: 生成完整视频场景配置
    3. Animation Coordinator: 添加动画效果（可选）
    
    输入端口:
        - data: DataFrame 数据（单个或多个）
        - task: 任务描述（自然语言）
    
    输出端口:
        - config: 视频配置 JSON（包含 meta, scenes, insights 等）
    
    主要特性:
        - 自然语言转视频配置
        - 支持多种图表类型（柱状图、折线图、饼图、散点图等）
        - 支持多 DataFrame 输入
        - 多智能体生成流程
        - 自动生成动画配置
        - 支持中英文输出
    
    Examples:
        >>> # 基本使用
        >>> node = NL2DVNode(
        ...     node_id="nl2dv1",
        ...     config={
        ...         "api_key": "sk-...",
        ...         "model": "gpt-4o",
        ...         "language": "English"
        ...     }
        ... )
        >>> 
        >>> df = pd.DataFrame({
        ...     'company': ['Apple', 'Microsoft', 'Google'],
        ...     'revenue': [394.3, 211.9, 307.4]
        ... })
        >>> 
        >>> outputs = node.run({
        ...     "data": NodeInput(data={"dataframe": df}),
        ...     "task": NodeInput(data={"description": "生成一个展示科技公司收入的视频"})
        ... })
        >>> 
        >>> config = outputs["config"].data
        >>> print(f"视频标题: {config['meta']['title']}")
        >>> print(f"场景数量: {len(config['scenes'])}")
        >>> 
        >>> # 多 DataFrame 输入
        >>> df1 = pd.DataFrame({'month': ['Jan', 'Feb'], 'sales': [100, 150]})
        >>> df2 = pd.DataFrame({'category': ['A', 'B'], 'value': [10, 20]})
        >>> 
        >>> outputs = node.run({
        ...     "data": NodeInput(data={"dataframe_list": [df1, df2]}),
        ...     "task": NodeInput(data={"description": "创建对比视频"})
        ... })
    """
    
    node_type = "NL2DV"
    
    def __init__(
        self,
        node_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """初始化 NL2DV 节点
        
        Args:
            node_id: 节点实例ID
            config: 节点配置字典，包含：
                - api_key: LLM API Key（如果为 None，从环境变量读取）
                - base_url: LLM API Base URL
                - model: LLM 模型名称
                - temperature: LLM 温度参数
                - language: 输出语言（English/Chinese）
                - skip_animations: 是否跳过动画生成
                - fps: 视频帧率（默认30）
                - width: 视频宽度（默认1280）
                - height: 视频高度（默认720）
                - verbose: 是否输出详细日志
        
        Raises:
            ValueError: API Key 未提供且环境变量也未设置
        """
        super().__init__(node_id, config)
        
        # 设置节点元数据
        self.metadata = NodeMetadata(
            name="NL2DV",
            display_name="自然语言转数据视频配置",
            description="使用 LLM 将自然语言描述和 DataFrame 转换为视频配置 JSON",
            category="video",
            tags=["llm", "video", "nl2dv", "ai", "visualization"],
            version="0.1.0",
            author="DeepEye",
            semantic_description=(
                "将自然语言任务描述和 DataFrame 数据转换为数据视频配置。"
                "支持多种图表类型和动画效果，自动生成完整的视频场景配置。"
            ),
            capabilities=["nl2config", "data_analysis", "scene_design", "animation"],
            input_description={
                "data": "输入的 DataFrame 或 DataFrame 列表",
                "task": "自然语言任务描述"
            },
            output_description={
                "config": "视频配置 JSON，包含 meta、scenes、insights 等"
            },
            use_cases=[
                "从数据生成数据视频配置",
                "自动创建数据可视化视频场景",
                "将数据分析结果转换为视频内容"
            ]
        )
        
        # 定义输入端口
        self.input_ports = [
            NodeInputPort(
                name="data",
                label="输入数据",
                required=True,
                schemas=[
                    NodeInputSchema(
                        name="dataframe",
                        type="object",
                        required=False,
                        description="待处理的单个 DataFrame 数据"
                    ),
                    NodeInputSchema(
                        name="dataframe_list",
                        type="array",
                        required=False,
                        description="待处理的多个 DataFrame 数据列表"
                    )
                ]
            ),
            NodeInputPort(
                name="task",
                label="任务描述",
                required=True,
                schemas=[
                    NodeInputSchema(
                        name="description",
                        type="string",
                        required=True,
                        description="自然语言描述的视频生成任务"
                    )
                ]
            )
        ]
        
        # 定义输出端口
        self.output_ports = [
            NodeOutputPort(
                name="config",
                label="视频配置",
                schemas=[
                    NodeOutputSchema(
                        name="config",
                        type="object",
                        description="视频配置 JSON，包含 meta、scenes、insights 等"
                    )
                ]
            )
        ]
        
        # 初始化 LLM 客户端
        api_key = self.config.api_key or os.getenv("DEEPEYE_LLM_API_KEY")
        if not api_key:
            raise ValueError(
                "未提供 API Key。请通过配置传入或设置环境变量 DEEPEYE_LLM_API_KEY"
            )
        
        self.llm_client = LLMClient(
            api_key=api_key,
            base_url=self.config.base_url,
            timeout=120  # 视频生成可能需要较长时间
        )
        
        # 初始化配置生成器
        self.generator = SimpleConfigGenerator(
            llm_client=self.llm_client,
            model=self.config.model
        )
    
    def _parse_config(self, config: Dict[str, Any]) -> NL2DVConfig:
        """解析配置
        
        Args:
            config: 配置字典
            
        Returns:
            NL2DVConfig 对象
        """
        return NL2DVConfig(**config)
    
    def execute(self, inputs: Dict[str, NodeInput]) -> Dict[str, NodeOutput]:
        """执行视频配置生成任务
        
        Args:
            inputs: 输入字典，包含：
                - data: 输入的 DataFrame 或 DataFrame 列表
                - task: 任务描述（自然语言）
        
        Returns:
            输出字典，包含：
                - config: 视频配置 JSON（成功时）或错误信息（失败时）
        """
        # 1. 提取输入
        try:
            data_input = inputs["data"].data
            task_input = inputs["task"].data["description"]
        except KeyError as e:
            return self.create_single_output(
                data=None,
                status=NodeStatus.FAILED,
                error=f"缺少必要的输入: {e}"
            )
        except Exception as e:
            return self.create_single_output(
                data=None,
                status=NodeStatus.FAILED,
                error=f"输入解析失败: {e}"
            )
        
        # 2. 判断是单 DataFrame 还是多 DataFrame 模式
        if isinstance(data_input, dict):
            if "dataframe" in data_input:
                # 单 DataFrame 模式
                dataframes = [data_input["dataframe"]]
            elif "dataframe_list" in data_input:
                # 多 DataFrame 模式
                dataframes = data_input["dataframe_list"]
            else:
                return self.create_single_output(
                    data=None,
                    status=NodeStatus.FAILED,
                    error="必须提供 'dataframe' 或 'dataframe_list'"
                )
        else:
            # 直接传入 DataFrame
            if isinstance(data_input, pd.DataFrame):
                dataframes = [data_input]
            elif isinstance(data_input, list):
                dataframes = data_input
            else:
                return self.create_single_output(
                    data=None,
                    status=NodeStatus.FAILED,
                    error=f"不支持的数据类型: {type(data_input).__name__}"
                )
        
        # 3. 验证 DataFrame 类型
        for i, df in enumerate(dataframes):
            if not isinstance(df, pd.DataFrame):
                return self.create_single_output(
                    data=None,
                    status=NodeStatus.FAILED,
                    error=f"DataFrame {i} 必须是 pandas.DataFrame，但得到 {type(df).__name__}"
                )
        
        # 4. 验证任务描述
        if not isinstance(task_input, str) or not task_input.strip():
            return self.create_single_output(
                data=None,
                status=NodeStatus.FAILED,
                error="task 必须是非空字符串"
            )
        
        # 5. 转换 DataFrame → List[Dict]
        # 对于多 DataFrame，合并或使用第一个（这里使用第一个）
        # TODO: 未来可以支持多 DataFrame 的合并策略
        if len(dataframes) > 1:
            if self.config.verbose:
                print(f"⚠️  检测到 {len(dataframes)} 个 DataFrame，使用第一个")
        
        df = dataframes[0]
        data = df.to_dict('records')
        
        # 6. 调用生成器生成配置
        try:
            config = self.generator.generate(
                query=task_input,
                data=data,
                language=self.config.language,
                verbose=self.config.verbose,
                skip_animations=self.config.skip_animations
            )
            
            # 7. 应用配置中的视频元数据（如果配置中没有，使用节点配置）
            if "meta" not in config:
                config["meta"] = {}
            
            # 如果配置中没有这些字段，使用节点配置的默认值
            if "fps" not in config["meta"]:
                config["meta"]["fps"] = self.config.fps
            if "width" not in config["meta"]:
                config["meta"]["width"] = self.config.width
            if "height" not in config["meta"]:
                config["meta"]["height"] = self.config.height
            
            # 8. 构建 metadata
            metadata = {
                "task_description": task_input,
                "language": self.config.language,
                "skip_animations": self.config.skip_animations,
                "num_scenes": len(config.get("scenes", [])),
                "input_shape": df.shape,
                "num_dataframes": len(dataframes)
            }
            
            # 统计动画数量
            total_animations = sum(
                len(scene.get("animations", [])) 
                for scene in config.get("scenes", [])
            )
            metadata["total_animations"] = total_animations
            
            # 9. 返回成功输出
            return self.create_single_output(
                data=config,
                status=NodeStatus.SUCCESS,
                metadata=metadata
            )
        
        except Exception as e:
            # 生成失败
            error_msg = str(e)
            if self.config.verbose:
                import traceback
                print(f"❌ 配置生成失败: {error_msg}")
                traceback.print_exc()
            
            return self.create_single_output(
                data=None,
                status=NodeStatus.FAILED,
                error=f"视频配置生成失败: {error_msg}",
                metadata={
                    "task_description": task_input,
                    "error_type": type(e).__name__
                }
            )

