"""DataPlot 专用代码执行器

基于 BaseCodeExecutor 实现的可视化图表生成执行器
采用 Code Filling 模式，将用户代码插入到预定义的模板中
"""

from typing import Optional, Tuple, List, Dict, Any
import pandas as pd
import pickle
import base64
from pathlib import Path
import re

from deepeye.runtime.code_executor import BaseCodeExecutor, GlobalSandboxContainer
from deepeye.utils import WorkspaceManager

try:
    from llm_sandbox import SandboxSession
    HAS_SANDBOX = True
except ImportError:
    HAS_SANDBOX = False


class PlotCodeExecutor(BaseCodeExecutor[List[pd.DataFrame], List[Dict[str, Any]]]):
    """可视化图表代码执行器
    
    专门用于数据可视化场景：
    - 输入：DataFrame 列表
    - 输出：图片列表（包含字节数据、文件名、描述等）
    - 自动处理文件传输
    - 采用 Code Filling 模式
    
    Example:
        >>> from deepeye.utils import WorkspaceManager
        >>> 
        >>> workspace = WorkspaceManager()
        >>> executor = PlotCodeExecutor(workspace_manager=workspace)
        >>> df = pd.DataFrame({'x': [1, 2, 3], 'y': [4, 5, 6]})
        >>> 
        >>> # 用户只需要提供核心可视化代码
        >>> user_code = '''
        ... import matplotlib.pyplot as plt
        ... 
        ... fig, ax = plt.subplots(figsize=(8, 6))
        ... ax.plot(df['x'], df['y'], marker='o')
        ... ax.set_title('X vs Y')
        ... ax.set_xlabel('X')
        ... ax.set_ylabel('Y')
        ... 
        ... # 保存图片
        ... filename = 'line_chart.png'
        ... plt.savefig(f'{PLOT_DIR}/{filename}', dpi=300, bbox_inches='tight')
        ... plt.close()
        ... 
        ... # 输出图片信息
        ... print(f'PLOT_FILE: {filename}|X和Y的折线图|png')
        ... '''
        >>> 
        >>> success, images, error = executor.execute(user_code, [df], execution_id="test-123")
        >>> assert success
        >>> assert len(images) == 1
        >>> assert images[0]['filename'] == 'line_chart.png'
        >>> assert 'file_path' in images[0]  # 持久化路径
    """
    
    def __init__(
        self,
        timeout: int = 60,
        libraries: Optional[List[str]] = None,
        verbose: bool = False,
        sandbox_plot_dir: str = "/sandbox/plots",
        workspace_manager: Optional[WorkspaceManager] = None
    ):
        """初始化执行器
        
        Args:
            timeout: 执行超时时间（秒）
            libraries: 需要的 Python 库列表
            verbose: 是否输出详细信息
            sandbox_plot_dir: 沙盒中的图片保存目录
            workspace_manager: 工作空间管理器，用于持久化图片文件
        """
        if libraries is None:
            libraries = ["matplotlib", "seaborn", "pandas", "numpy"]
        
        super().__init__(timeout=timeout, libraries=libraries, verbose=verbose)
        self.sandbox_plot_dir = sandbox_plot_dir
        self.workspace_manager = workspace_manager or WorkspaceManager()
    
    def _prepare_code(self, user_code: str, dataframes: List[pd.DataFrame]) -> str:
        """准备代码：将用户代码插入到模板中
        
        采用 Code Filling 模式：
        1. 模板前部分：导入库 + 反序列化 DataFrame
        2. 用户代码：核心可视化逻辑
        3. 模板后部分：（无需额外处理）
        
        Args:
            user_code: 用户提供的可视化代码（LLM 生成）
            dataframes: DataFrame 列表
        
        Returns:
            完整的可执行代码
        """
        # 序列化所有 DataFrame
        encoded_dfs = []
        for df in dataframes:
            df_encoded = base64.b64encode(pickle.dumps(df)).decode()
            encoded_dfs.append(df_encoded)
        
        # 构建 DataFrame 初始化代码
        if len(dataframes) == 1:
            # 单 DataFrame 模式
            df_init_code = f"""
# === Input DataFrame is deserialized and available as 'df' ===
df_encoded = '''{encoded_dfs[0]}'''
df = pickle.loads(base64.b64decode(df_encoded.encode()))
dataframe = df  # 提供别名
"""
        else:
            # 多 DataFrame 模式
            df_init_lines = ["# === Input DataFrames are deserialized and available as 'df0', 'df1', 'df2', ... ==="]
            for i, encoded in enumerate(encoded_dfs):
                df_init_lines.append(f"df{i}_encoded = '''{encoded}'''")
                df_init_lines.append(f"df{i} = pickle.loads(base64.b64decode(df{i}_encoded.encode()))")
            df_init_code = "\n".join(df_init_lines)
        
        # 构建完整代码（Code Filling 模式）
        full_code = f"""
import pandas as pd
import numpy as np
import pickle
import base64
import os
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns

{df_init_code}

# === Plot directory is prepared ===
PLOT_DIR = "{self.sandbox_plot_dir}"
os.makedirs(PLOT_DIR, exist_ok=True)

# === YOUR CODE WILL BE INSERTED HERE ===
{user_code}
# === END OF YOUR CODE ===

# === Output validation (automatically handled) ===
# The system will automatically collect all saved plot files
"""
        return full_code
    
    def _extract_result(self, output: str) -> List[Dict[str, Any]]:
        """从输出中提取图片信息（仅解析，不读取文件）
        
        Args:
            output: 沙盒执行的 stdout 输出
        
        Returns:
            图片信息列表（不包含实际字节数据）
            
        Raises:
            ValueError: 如果输出格式不正确
        
        Note:
            期望的输出格式：
            PLOT_FILE: filename.png|描述|格式
            或
            PLOT_FILE: filename.png|描述
        """
        images = []
        
        # 使用正则表达式提取所有 PLOT_FILE 行
        pattern = r'PLOT_FILE:\s*([^|]+)\|([^|]+)(?:\|([^|\n]+))?'
        matches = re.findall(pattern, output)
        
        if not matches:
            raise ValueError(
                f"输出中未找到图片信息标记。\n"
                f"请确保代码中包含：\n"
                f"print('PLOT_FILE: filename.png|描述|格式')\n\n"
                f"实际输出: {output[:500]}..."
            )
        
        for match in matches:
            filename = match[0].strip()
            description = match[1].strip()
            format_hint = match[2].strip() if len(match) > 2 and match[2] else None
            
            images.append({
                "filename": filename,
                "description": description,
                "format_hint": format_hint
            })
        
        if not images:
            raise ValueError("未找到任何图片信息")
        
        return images
    
    def _finalize_result(
        self,
        session: 'SandboxSession',
        preliminary_result: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """从沙盒复制图片文件到本地并读取内容
        
        Args:
            session: SandboxSession对象，用于文件复制
            preliminary_result: _extract_result返回的图片信息列表
        
        Returns:
            完整的图片信息列表，包含实际字节数据和文件路径
            
        Raises:
            Exception: 如果文件复制或读取失败
        """
        # 获取持久化目录（自动生成UUID）
        plot_dir = self.workspace_manager.get_plot_dir()
        
        # 从沙盒复制图片文件到持久化目录
        images = []
        for img_info in preliminary_result:
            filename = img_info["filename"]
            sandbox_path = f"{self.sandbox_plot_dir}/{filename}"
            local_path = plot_dir / filename
            
            # 从沙盒复制文件到持久化目录
            session.copy_from_runtime(sandbox_path, str(local_path))
            
            # 读取文件内容
            with open(local_path, "rb") as f:
                image_data = f.read()
            
            # 推断图片格式
            file_ext = Path(filename).suffix.lower().lstrip('.')
            if not file_ext:
                # 如果文件名没有扩展名，尝试从 format_hint 获取
                file_ext = img_info.get("format_hint", "png")
            
            # 构建完整的图片信息
            images.append({
                "data": image_data,
                "filename": filename,
                "description": img_info["description"],
                "format": file_ext,
                "file_size": len(image_data),
                "file_path": str(local_path)  # 持久化路径
            })
        
        if not images:
            raise ValueError("未生成任何图片")
        
        return images

