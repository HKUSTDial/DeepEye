"""DataPlot 节点实现 - 智能数据可视化

该节点接收自然语言描述和 DataFrame，通过 LLM 生成 Python 可视化代码并执行。
包含多轮错误修复机制，自动处理图片生成和提取。

采用 Code Filling 任务设计，LLM 只需生成核心可视化代码，
DataFrame 的准备和环境设置由模板自动处理。
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
from deepeye.nodes.dataplot.executor import PlotCodeExecutor
from deepeye.llm import LLMClient, Message
from deepeye.nodes.dataplot.prompt import (
    format_initial_prompt,
    format_fix_prompt,
    extract_response_parts,
)
from deepeye.utils import WorkspaceManager
from deepeye.nodes.registry import register_node


class DataPlotConfig(NodeConfig):
    """DataPlot 节点配置"""
    
    # LLM 配置
    api_key: Optional[str] = None
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4"
    temperature: float = 0.1
    
    # 执行配置
    max_retries: int = 3
    timeout: int = 60
    libraries: Optional[List[str]] = None
    
    # 可视化配置
    sandbox_plot_dir: str = "/sandbox/plots"
    
    # 调试配置
    verbose: bool = False


@register_node
class DataPlotNode(BaseNode):
    """DataPlot 节点 - 智能数据可视化
    
    该节点接收自然语言描述和 DataFrame，通过 LLM 生成 Python 可视化代码并执行。
    包含多轮错误修复机制，自动处理图片生成和提取。
    
    采用 Code Filling 任务设计：
    - LLM 只需生成核心可视化代码
    - DataFrame 变量（df/df0/df1/...）已经准备好
    - PLOT_DIR 变量已经设置好
    - 只需要专注于可视化逻辑
    
    输入端口:
        - data: DataFrame 数据（单个或多个）
        - task: 任务描述（自然语言）
    
    输出端口:
        - images: 生成的图片列表
    
    主要特性:
        - 自然语言转可视化代码
        - 支持多种图表类型（折线图、柱状图、散点图、热力图等）
        - 支持多 DataFrame 输入
        - 支持一次生成多个图表
        - 多轮错误修复机制
        - 基于 Docker 的安全代码执行
        - Code Filling 模式，LLM 更容易理解上下文
    
    Examples:
        >>> # 基本使用 - 单图
        >>> node = DataPlotNode(
        ...     node_id="plot1",
        ...     config={
        ...         "api_key": "sk-...",
        ...         "model": "gpt-4"
        ...     }
        ... )
        >>> 
        >>> df = pd.DataFrame({
        ...     'month': ['Jan', 'Feb', 'Mar', 'Apr'],
        ...     'sales': [100, 150, 120, 180]
        ... })
        >>> 
        >>> outputs = node.run({
        ...     "data": NodeInput(data={"dataframe": df}),
        ...     "task": NodeInput(data={"description": "绘制月度销售额折线图"})
        ... })
        >>> 
        >>> images = outputs["images"].data
        >>> print(f"生成了 {len(images)} 个图片")
        >>> print(f"第一个图片: {images[0]['filename']}")
        >>> print(f"描述: {images[0]['description']}")
        >>> 
        >>> # 保存图片
        >>> with open("sales_chart.png", "wb") as f:
        ...     f.write(images[0]['data'])
        
        >>> # 多 DataFrame 多图
        >>> df1 = pd.DataFrame({'x': [1, 2, 3], 'y': [4, 5, 6]})
        >>> df2 = pd.DataFrame({'category': ['A', 'B', 'C'], 'value': [10, 20, 15]})
        >>> 
        >>> outputs = node.run({
        ...     "data": NodeInput(data={"dataframe_list": [df1, df2]}),
        ...     "task": NodeInput(data={
        ...         "description": "创建两个子图：df0的散点图和df1的柱状图"
        ...     })
        ... })
        >>> 
        >>> images = outputs["images"].data
        >>> print(f"生成了 {len(images)} 个图片")
    """
    
    node_type = "DataPlot"
    
    def __init__(
        self,
        node_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        validate_on_init: bool = False,
    ):
        """初始化 DataPlot 节点
        
        Args:
            node_id: 节点实例ID
            config: 节点配置字典，包含：
                - api_key: LLM API Key（如果为 None，从环境变量读取）
                - base_url: LLM API Base URL
                - model: LLM 模型名称
                - temperature: LLM 温度参数
                - max_retries: 最大错误修复重试次数
                - timeout: 代码执行超时时间
                - libraries: 可用的 Python 库列表
                - sandbox_plot_dir: 沙盒中的图片保存目录
                - verbose: 是否输出详细日志
            validate_on_init: 是否在初始化时验证配置（默认False，延迟到执行时验证）
        
        Raises:
            ValueError: API Key 未提供且环境变量也未设置
        """
        super().__init__(node_id, config, validate_on_init=validate_on_init)
        
        # 设置节点元数据
        self.metadata = NodeMetadata(
            name="DataPlot",
            display_name="智能数据可视化",
            description="使用 LLM 将自然语言描述转换为可视化代码并执行，生成图表图片",
            category="visualization",
            tags=["llm", "visualization", "plotting", "ai"],
            version="0.1.0",
            author="DeepEye"
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
                        description="待可视化的单个 DataFrame 数据"
                    ),
                    NodeInputSchema(
                        name="dataframe_list",
                        type="array",
                        required=False,
                        description="待可视化的多个 DataFrame 数据列表"
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
                        description="自然语言描述的可视化任务"
                    )
                ]
            )
        ]
        
        # 定义输出端口
        self.output_ports = [
            NodeOutputPort(
                name="images",
                label="生成的图片",
                schemas=[
                    NodeOutputSchema(
                        name="images",
                        type="array",
                        description="生成的图片列表，每个包含 data（字节）、filename、description 等"
                    )
                ]
            )
        ]
        
        # 初始化 LLM 客户端
        api_key = self.config.api_key or os.getenv("DEEPEYE_LLM_API_KEY")
        
        self.llm_client = LLMClient(
            api_key=api_key,
            base_url=self.config.base_url,
            timeout=self.config.timeout
        )
        
        # 初始化 WorkspaceManager
        self.workspace_manager = WorkspaceManager()
        
        # 初始化 PlotCodeExecutor
        libraries = self.config.libraries or [
            "matplotlib",
            "seaborn",
            "pandas",
            "numpy"
        ]
        
        self.executor = PlotCodeExecutor(
            libraries=libraries,
            timeout=self.config.timeout,
            verbose=self.config.verbose,
            sandbox_plot_dir=self.config.sandbox_plot_dir,
            workspace_manager=self.workspace_manager
        )
    
    def _parse_config(self, config: Dict[str, Any]) -> DataPlotConfig:
        """解析配置
        
        Args:
            config: 配置字典
            
        Returns:
            DataPlotConfig 对象
        """
        return DataPlotConfig(**config)
    
    def execute(self, inputs: Dict[str, NodeInput]) -> Dict[str, NodeOutput]:
        """执行可视化任务
        
        Args:
            inputs: 输入字典，包含：
                - data: 输入的 DataFrame 或 DataFrame 列表
                - task: 任务描述（自然语言）
        
        Returns:
            输出字典，包含：
                - images: 生成的图片列表（成功时）或错误信息（失败时）
        """
        # 提取输入
        data_input = inputs["data"].data
        task_input = inputs["task"].data["description"]
        
        # 判断是单 DataFrame 还是多 DataFrame 模式
        if "dataframe" in data_input:
            # 单 DataFrame 模式
            dataframes = [data_input["dataframe"]]
            is_multi_mode = False
        elif "dataframe_list" in data_input:
            # 多 DataFrame 模式
            dataframes = data_input["dataframe_list"]
            is_multi_mode = True
        else:
            return self.create_single_output(
                data=None,
                status=NodeStatus.FAILED,
                error="必须提供 'dataframe' 或 'dataframe_list'"
            )
        
        task_description = task_input
        
        # 验证输入类型
        if not isinstance(dataframes, list):
            dataframes = [dataframes]
        
        for i, df in enumerate(dataframes):
            if not isinstance(df, pd.DataFrame):
                return self.create_single_output(
                    data=None,
                    status=NodeStatus.FAILED,
                    error=f"DataFrame {i} 必须是 pandas.DataFrame，但得到 {type(df).__name__}"
                )
        
        if not isinstance(task_description, str):
            return self.create_single_output(
                data=None,
                status=NodeStatus.FAILED,
                error=f"task 必须是字符串，但得到 {type(task_description).__name__}"
            )
        
        # 生成数据信息
        if is_multi_mode:
            data_info = self._get_multi_dataframe_info(dataframes)
        else:
            data_info = self._get_dataframe_info(dataframes[0])
        
        # 第一轮：生成初始代码
        code, think_content, packages = self._generate_code(
            task_description,
            data_info,
            is_multi_mode
        )
        
        execution_log = []
        
        # 尝试执行代码，带多轮错误修复
        for retry in range(self.config.max_retries + 1):
            if self.config.verbose:
                print(f"\n{'='*60}")
                print(f"第 {retry + 1} 轮执行")
                print(f"{'='*60}")
                if think_content:
                    print(f"思考过程:\n{think_content}\n")
                print(f"使用的包: {packages}")
                print(f"代码:\n{code}")
            
            # 执行代码
            success, images, error = self.executor.execute(
                code,
                dataframes,
                additional_libraries=packages
            )
            
            # 记录执行日志
            log_entry = {
                "retry": retry,
                "code": code,
                "think": think_content,
                "packages": packages,
                "success": success,
                "error": error if not success else None,
                "image_count": len(images) if success else 0
            }
            execution_log.append(log_entry)
            
            if success:
                # 成功！
                if self.config.verbose:
                    print(f"\n✅ 执行成功！")
                    print(f"生成了 {len(images)} 个图片:")
                    for img in images:
                        print(f"  - {img['filename']}: {img['description']}")
                
                # 构建 metadata（仅包含有用的元信息）
                metadata = {
                    "code": code,
                    "packages": packages,
                    "task_description": task_description,
                    "image_count": len(images),
                    "is_multi_mode": is_multi_mode
                }
                
                if is_multi_mode:
                    metadata["input_shapes"] = [df.shape for df in dataframes]
                    metadata["num_dataframes"] = len(dataframes)
                else:
                    metadata["input_shape"] = dataframes[0].shape
                
                # 构建 metrics（执行指标）
                metrics = {
                    "retries": retry,
                    "execution_attempts": retry + 1,
                    "images_generated": len(images)
                }
                
                # 构建 logs
                logs = []
                for i, log in enumerate(execution_log):
                    if log["success"]:
                        logs.append(f"第 {i + 1} 次执行成功，生成 {log['image_count']} 个图片")
                    else:
                        logs.append(f"第 {i + 1} 次执行失败: {log['error']}")
                
                return self.create_single_output(
                    data=images,
                    status=NodeStatus.SUCCESS,
                    metadata=metadata,
                    metrics=metrics,
                    logs=logs
                )
            
            # 失败了，尝试修复
            if self.config.verbose:
                print(f"\n❌ 执行失败: {error}")
            
            if retry < self.config.max_retries:
                if self.config.verbose:
                    print(f"尝试修复...")
                
                code, think_content, packages = self._fix_code(
                    task_description,
                    data_info,
                    code,
                    error,
                    is_multi_mode
                )
            else:
                # 达到最大重试次数
                if self.config.verbose:
                    print(f"\n⚠️  达到最大重试次数 ({self.config.max_retries})")
                
                # 构建 metadata
                metadata = {
                    "code": code,
                    "task_description": task_description
                }
                
                # 构建 metrics
                metrics = {
                    "retries": retry,
                    "execution_attempts": retry + 1
                }
                
                # 构建 logs
                logs = []
                for i, log in enumerate(execution_log):
                    if log["success"]:
                        logs.append(f"第 {i + 1} 次执行成功，生成 {log['image_count']} 个图片")
                    else:
                        logs.append(f"第 {i + 1} 次执行失败: {log['error']}")
                
                return self.create_single_output(
                    data=None,
                    status=NodeStatus.FAILED,
                    error=f"代码执行失败，已重试 {self.config.max_retries} 次。最后的错误: {error}",
                    metadata=metadata,
                    metrics=metrics,
                    logs=logs
                )
        
        # 理论上不会到这里
        return self.create_single_output(
            data=None,
            status=NodeStatus.FAILED,
            error="未知错误"
        )
    
    def _get_dataframe_info(self, df: pd.DataFrame) -> str:
        """获取 DataFrame 的详细信息
        
        Args:
            df: 输入的 DataFrame
        
        Returns:
            DataFrame 信息的字符串描述
        """
        info_parts = [
            f"形状: {df.shape}",
            f"\n列信息:",
        ]
        
        for col in df.columns:
            dtype = df[col].dtype
            null_count = df[col].isna().sum()
            unique_count = df[col].nunique()
            
            col_info = f"  - {col}: {dtype}"
            if null_count > 0:
                col_info += f", {null_count} 个空值"
            col_info += f", {unique_count} 个唯一值"
            
            # 添加示例值
            if dtype in ['object', 'string']:
                sample_values = df[col].dropna().head(3).tolist()
                if sample_values:
                    col_info += f", 示例: {sample_values}"
            elif dtype in ['int64', 'float64']:
                col_info += f", 范围: [{df[col].min()}, {df[col].max()}]"
            
            info_parts.append(col_info)
        
        # 添加前几行数据
        info_parts.append(f"\n前 5 行数据:\n{df.head().to_string()}")
        
        return "\n".join(info_parts)
    
    def _get_multi_dataframe_info(self, dataframes: List[pd.DataFrame]) -> str:
        """获取多个 DataFrame 的详细信息
        
        Args:
            dataframes: DataFrame 列表
        
        Returns:
            多个 DataFrame 信息的字符串描述
        """
        info_parts = [f"共有 {len(dataframes)} 个 DataFrame:\n"]
        
        for i, df in enumerate(dataframes):
            info_parts.append(f"\n{'='*60}")
            info_parts.append(f"DataFrame {i} (变量名: df{i}):")
            info_parts.append(f"{'='*60}")
            info_parts.append(self._get_dataframe_info(df))
        
        return "\n".join(info_parts)
    
    def _generate_code(
        self,
        task_description: str,
        data_info: str,
        is_multi_mode: bool = False
    ) -> tuple[str, str, list[str]]:
        """生成初始代码
        
        Args:
            task_description: 任务描述
            data_info: DataFrame 信息
            is_multi_mode: 是否为多 DataFrame 模式
        
        Returns:
            (代码, 思考过程, 包列表) 元组
        """
        user_prompt = format_initial_prompt(
            task_description=task_description,
            data_info=data_info,
            is_multi_mode=is_multi_mode
        )
        
        response = self.llm_client.generate(
            messages=[Message(role="user", content=user_prompt)],
            model=self.config.model,
            temperature=self.config.temperature
        )
        
        think_content, package_list, code = extract_response_parts(response.content)
        
        return code, think_content, package_list
    
    def _fix_code(
        self,
        task_description: str,
        data_info: str,
        failed_code: str,
        error_message: str,
        is_multi_mode: bool = False
    ) -> tuple[str, str, list[str]]:
        """修复失败的代码
        
        Args:
            task_description: 任务描述
            data_info: DataFrame 信息
            failed_code: 失败的代码
            error_message: 错误信息
            is_multi_mode: 是否为多 DataFrame 模式
        
        Returns:
            (修复后的代码, 思考过程, 包列表) 元组
        """
        fix_prompt = format_fix_prompt(
            task_description=task_description,
            data_info=data_info,
            failed_code=failed_code,
            error_message=error_message,
            is_multi_mode=is_multi_mode
        )
        
        response = self.llm_client.generate(
            messages=[Message(role="user", content=fix_prompt)],
            model=self.config.model,
            temperature=self.config.temperature
        )
        
        think_content, package_list, code = extract_response_parts(response.content)
        
        return code, think_content, package_list

