"""文件数据源节点

从文件系统或URL读取数据文件。
支持的格式：CSV, JSON, Excel
"""

from typing import Optional, Union, List, Dict, Any
from pathlib import Path
import pandas as pd
from urllib.parse import urlparse

from deepeye.nodes.base import NodeMetadata
from deepeye.nodes.datasource.base import BaseDataSourceNode, DataSourceConfig
from deepeye.nodes.registry import register_node


class FileDataSourceConfig(DataSourceConfig):
    """文件数据源配置
    
    Attributes:
        file_path: 文件路径或URL
        file_type: 文件类型（auto自动检测，csv, json, excel）
        
        # CSV特定选项
        delimiter: CSV分隔符
        encoding: 文件编码
        header: CSV表头行号
        
        # Excel特定选项
        sheet_name: Excel工作表名称或索引
        
        # JSON特定选项
        json_orient: JSON格式方向
        
        # 通用选项
        nrows: 读取的最大行数
        usecols: 读取的列名列表
        
        # 安全和性能
        allow_remote: 是否允许从URL读取
    """
    
    file_path: Optional[str] = None
    file_type: str = "auto"
    
    # CSV特定选项
    delimiter: str = ","
    encoding: str = "utf-8"
    header: Union[int, None, str] = 0
    
    # Excel特定选项
    sheet_name: Union[str, int] = 0
    
    # JSON特定选项
    json_orient: Optional[str] = None
    
    # 通用选项
    nrows: Optional[int] = None
    usecols: Optional[List[str]] = None
    
    # 安全和性能
    allow_remote: bool = True


@register_node
class FileDataSourceNode(BaseDataSourceNode):
    """文件数据源节点
    
    从本地文件或URL读取数据，支持：
    - CSV (.csv)
    - JSON (.json)
    - Excel (.xlsx, .xls)
    
    特点:
    - 自动检测文件类型
    - 支持HTTP/HTTPS URL
    - 内存保护（行数限制）
    - 灵活的读取选项
    
    Example:
        >>> # 读取本地CSV文件
        >>> node = FileDataSourceNode(
        ...     node_id="sales",
        ...     config={"file_path": "data/sales.csv"}
        ... )
        >>> result = node.run(inputs={})
        >>> df = result["data"].data["dataframe"]
        
        >>> # 从URL读取
        >>> node = FileDataSourceNode(
        ...     node_id="remote",
        ...     config={"file_path": "https://example.com/data.csv"}
        ... )
        
        >>> # 指定读取选项
        >>> node = FileDataSourceNode(
        ...     node_id="custom",
        ...     config={
        ...         "file_path": "data.csv",
        ...         "nrows": 1000,           # 只读1000行
        ...         "encoding": "utf-8",      # 指定编码
        ...         "delimiter": ";",         # 自定义分隔符
        ...         "usecols": ["name", "age"]  # 只读特定列
        ...     }
        ... )
    """
    
    node_type = "FileDataSource"
    
    def __init__(
        self,
        node_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        validate_on_init: bool = False,
    ):
        """初始化文件数据源节点
        
        Args:
            node_id: 节点实例ID
            config: 节点配置字典，包含：
                - file_path: 文件路径或URL
                - file_type: 文件类型（auto自动检测，csv, json, excel）
                - delimiter: CSV分隔符
                - encoding: 文件编码
                - header: CSV表头行号（0为第一行，None为无表头）
                - sheet_name: Excel工作表名称或索引
                - json_orient: JSON格式方向
                - nrows: 读取的最大行数
                - usecols: 读取的列名列表
                - max_rows: 绝对最大行数限制
                - allow_remote: 是否允许从URL读取
            validate_on_init: 是否在初始化时验证配置（默认False，延迟到执行时验证）
        
        Raises:
            ValueError: 文件路径为空或格式不支持
        """
        super().__init__(node_id, config, validate_on_init=validate_on_init)
        
        # 设置节点元数据
        self.metadata = NodeMetadata(
            name="FileDataSource",
            display_name="文件数据源",
            description="从本地文件或URL读取数据（支持CSV、JSON、Excel）",
            category="datasource",
            tags=["file", "csv", "json", "excel"],
            version="0.1.0",
            author="DeepEye"
        )
        
        # 注意：配置验证已延迟到 execute 时进行，允许运行时动态配置
    
    def _parse_config(self, config: Dict[str, Any]) -> FileDataSourceConfig:
        """解析配置
        
        Args:
            config: 配置字典
            
        Returns:
            FileDataSourceConfig 对象
        """
        return FileDataSourceConfig(**config)
    
    def _validate_config(self):
        """验证配置参数"""
        if not self.config.file_path:
            raise ValueError("file_path 参数不能为空")
        
        # 验证URL权限
        if self._is_url(self.config.file_path) and not self.config.allow_remote:
            raise ValueError(
                f"不允许从URL读取数据。设置 allow_remote=True 以启用。"
            )
        
        # 验证行数限制
        if self.config.nrows is not None:
            if self.config.nrows <= 0:
                raise ValueError(f"nrows 必须为正数，但得到: {self.config.nrows}")
            if self.config.nrows > self.config.max_rows:
                raise ValueError(
                    f"nrows ({self.config.nrows}) 超过最大限制 ({self.config.max_rows})"
                )
    
    def _is_url(self, path: str) -> bool:
        """检查路径是否为URL
        
        Args:
            path: 文件路径
        
        Returns:
            是否为URL
        """
        try:
            result = urlparse(path)
            return result.scheme in ('http', 'https', 'ftp')
        except Exception:
            return False
    
    def _detect_file_type(self, path: str) -> str:
        """自动检测文件类型
        
        Args:
            path: 文件路径
        
        Returns:
            文件类型（csv, json, excel）
        
        Raises:
            ValueError: 无法识别的文件类型
        """
        path_lower = path.lower()
        
        if path_lower.endswith('.csv'):
            return 'csv'
        elif path_lower.endswith('.json'):
            return 'json'
        elif path_lower.endswith(('.xlsx', '.xls')):
            return 'excel'
        else:
            raise ValueError(
                f"无法识别文件类型: {path}。"
                f"支持的格式: .csv, .json, .xlsx, .xls"
            )
    
    def _load_data(self) -> pd.DataFrame:
        """加载文件数据
        
        Returns:
            DataFrame格式的数据
        
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式不支持
            Exception: 读取错误
        """
        # 确定文件类型
        if self.config.file_type == "auto":
            file_type = self._detect_file_type(self.config.file_path)
        else:
            file_type = self.config.file_type.lower()
        
        # 根据类型读取
        if file_type == "csv":
            return self._load_csv()
        elif file_type == "json":
            return self._load_json()
        elif file_type == "excel":
            return self._load_excel()
        else:
            raise ValueError(f"不支持的文件类型: {file_type}")
    
    def _load_csv(self) -> pd.DataFrame:
        """读取CSV文件
        
        Returns:
            DataFrame
        """
        try:
            df = pd.read_csv(
                self.config.file_path,
                delimiter=self.config.delimiter,
                encoding=self.config.encoding,
                header=self.config.header if self.config.header != 'infer' else 0,
                nrows=self.config.nrows,
                usecols=self.config.usecols,
            )
            return df
        except FileNotFoundError:
            raise FileNotFoundError(f"文件不存在: {self.config.file_path}")
        except UnicodeDecodeError as e:
            raise ValueError(
                f"文件编码错误。当前编码: {self.config.encoding}。"
                f"请尝试其他编码（如 'gbk', 'latin1'）。错误: {e}"
            )
        except Exception as e:
            raise Exception(f"读取CSV文件失败: {e}")
    
    def _load_json(self) -> pd.DataFrame:
        """读取JSON文件
        
        Returns:
            DataFrame
        """
        try:
            df = pd.read_json(
                self.config.file_path,
                orient=self.config.json_orient,
                encoding=self.config.encoding,
            )
            
            # 应用行列限制
            if self.config.nrows is not None:
                df = df.head(self.config.nrows)
            if self.config.usecols is not None:
                df = df[self.config.usecols]
            
            return df
        except FileNotFoundError:
            raise FileNotFoundError(f"文件不存在: {self.config.file_path}")
        except ValueError as e:
            raise ValueError(f"JSON格式错误: {e}")
        except Exception as e:
            raise Exception(f"读取JSON文件失败: {e}")
    
    def _load_excel(self) -> pd.DataFrame:
        """读取Excel文件
        
        Returns:
            DataFrame
        
        Raises:
            ImportError: openpyxl未安装
        """
        try:
            df = pd.read_excel(
                self.config.file_path,
                sheet_name=self.config.sheet_name,
                header=self.config.header if self.config.header != 'infer' else 0,
                nrows=self.config.nrows,
                usecols=self.config.usecols,
            )
            return df
        except ImportError:
            raise ImportError(
                "读取Excel文件需要 openpyxl 库。"
                "请安装: uv pip install openpyxl"
            )
        except FileNotFoundError:
            raise FileNotFoundError(f"文件不存在: {self.config.file_path}")
        except Exception as e:
            raise Exception(f"读取Excel文件失败: {e}")
    
    def _get_source_info(self) -> Dict[str, Any]:
        """获取数据源信息
        
        Returns:
            数据源的详细信息
        """
        info = {
            "source": "file",
            "file_path": self.config.file_path,
            "file_type": self.config.file_type,
            "is_remote": self._is_url(self.config.file_path),
        }
        
        # 添加读取选项
        if self.config.nrows is not None:
            info["nrows_limit"] = self.config.nrows
        if self.config.usecols is not None:
            info["selected_columns"] = self.config.usecols
        
        # CSV特定信息
        if self.config.file_type in ("auto", "csv"):
            info["csv_options"] = {
                "delimiter": self.config.delimiter,
                "encoding": self.config.encoding,
                "header": self.config.header,
            }
        
        # Excel特定信息
        if self.config.file_type in ("auto", "excel"):
            info["excel_options"] = {
                "sheet_name": self.config.sheet_name,
            }
        
        return info
