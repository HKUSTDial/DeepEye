"""NL2SQL 节点实现 - 自然语言转 SQL

该节点接收数据库 schema 信息和用户问题，生成 SQL 查询并执行。
包含多轮错误修复机制，自动处理 SQL 执行错误。
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
from deepeye.nodes.database.connection import DatabaseConnection
from deepeye.llm import LLMClient, Message
from deepeye.nodes.nl2sql.prompt import (
    format_initial_prompt,
    format_fix_prompt,
    extract_response_parts,
)


class NL2SQLConfig(NodeConfig):
    """NL2SQL 节点配置"""
    
    # LLM 配置
    api_key: Optional[str] = None
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4"
    temperature: float = 0.0  # 使用 0 温度以获得确定性输出
    
    # 执行配置
    max_retries: int = 3
    timeout: int = 60
    max_rows: int = 100000  # 查询结果的最大行数
    
    # 调试选项
    verbose: bool = False


class NL2SQLNode(BaseNode):
    """NL2SQL 节点 - 自然语言转 SQL
    
    该节点接收数据库 schema 信息和用户的自然语言问题，
    通过 LLM 生成 SQL 查询，执行并返回结果。
    包含多轮错误修复机制，自动处理 SQL 执行错误。
    
    输入端口:
        - connection_string: 数据库连接字符串
        - database_info: 数据库信息（schema, examples, statistics）
        - query: 用户的自然语言问题
    
    输出端口:
        - sql: 生成的 SQL 查询
        - data: 查询结果 DataFrame
        - explanation: SQL 的自然语言解释
    
    主要特性:
        - 自然语言转 SQL
        - 支持多种数据库方言（SQLite, MySQL, PostgreSQL）
        - Schema-aware prompt engineering
        - 多轮错误修复机制
        - 自动处理常见 SQL 错误
    
    Examples:
        >>> # 基本使用
        >>> node = NL2SQLNode(
        ...     node_id="nl2sql1",
        ...     config={
        ...         "api_key": "sk-...",
        ...         "model": "gpt-4"
        ...     }
        ... )
        >>> 
        >>> # 从 DatabaseDataSourceNode 获取输入
        >>> outputs = node.run({
        ...     "connection_string": NodeInput(data="sqlite:///sales.db"),
        ...     "database_info": NodeInput(data={
        ...         "schema": {...},
        ...         "examples": {...},
        ...         "statistics": {...}
        ...     }),
        ...     "query": NodeInput(data="找出销售额前10的产品")
        ... })
        >>> 
        >>> # 获取结果
        >>> sql_output = outputs["sql"]
        >>> data_output = outputs["data"]
        >>> 
        >>> if data_output.status == NodeStatus.SUCCESS:
        ...     print(f"生成的 SQL: {sql_output.data}")
        ...     print(f"查询结果:")
        ...     print(data_output.data)  # DataFrame
        ...     print(f"重试次数: {data_output.metadata.get('retries', 0)}")
        ... else:
        ...     print(f"执行失败: {data_output.error}")
    """
    
    node_type = "NL2SQL"
    
    def __init__(
        self,
        node_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """初始化 NL2SQL 节点
        
        Args:
            node_id: 节点实例ID
            config: 节点配置字典，包含：
                - api_key: LLM API 密钥
                - base_url: LLM API 基础URL
                - model: LLM 模型名称
                - temperature: LLM 温度参数
                - max_retries: 最大重试次数
                - timeout: 超时时间（秒）
                - max_rows: 查询结果的最大行数
                - verbose: 是否输出详细日志
        """
        super().__init__(node_id, config)
        
        # 设置节点元数据
        self.metadata = NodeMetadata(
            name="NL2SQL",
            display_name="NL2SQL 节点",
            description="将自然语言问题转换为 SQL 查询并执行",
            category="processing",
            tags=["sql", "llm", "database", "query"],
            version="0.1.0",
            author="DeepEye"
        )
        
        # 定义输入端口
        # 第一个端口：database - 包含数据库连接和信息
        # 第二个端口：query - 用户的自然语言问题
        self.input_ports = [
            NodeInputPort(
                name="database",
                label="数据库",
                schemas=[
                    NodeInputSchema(
                        name="connection_string",
                        type="string",
                        description="数据库连接字符串"
                    ),
                    NodeInputSchema(
                        name="database_info",
                        type="object",
                        description="数据库 schema、示例数据、统计信息"
                    )
                ],
                required=True
            ),
            NodeInputPort(
                name="query",
                label="用户问题",
                schemas=[
                    NodeInputSchema(
                        name="query",
                        type="string",
                        description="用户的自然语言问题"
                    )
                ],
                required=True
            )
        ]
        
        # 定义输出端口
        # 只有一个端口：data - 包含 sql、dataframe 和 explanation
        self.output_ports = [
            NodeOutputPort(
                name="data",
                label="输出数据",
                schemas=[
                    NodeOutputSchema(
                        name="sql",
                        type="string",
                        description="生成的 SQL 查询语句"
                    ),
                    NodeOutputSchema(
                        name="dataframe",
                        type="object",
                        description="SQL 查询结果 DataFrame"
                    ),
                    NodeOutputSchema(
                        name="explanation",
                        type="string",
                        description="SQL 的自然语言解释"
                    )
                ]
            )
        ]
        
        # 初始化 LLM 客户端
        api_key = self.config.api_key or os.getenv("DEEPEYE_LLM_API_KEY")
        if not api_key:
            raise ValueError(
                "NL2SQL 节点需要 API Key。"
                "请通过 config['api_key'] 或环境变量 DEEPEYE_LLM_API_KEY 提供。"
            )
        
        self.llm_client = LLMClient(
            api_key=api_key,
            base_url=self.config.base_url,
        )
        
        # 数据库连接（延迟初始化）
        self.db_connection: Optional[DatabaseConnection] = None
    
    def _parse_config(self, config: Dict[str, Any]) -> NL2SQLConfig:
        """解析配置
        
        Args:
            config: 配置字典
        
        Returns:
            NL2SQLConfig 对象
        """
        return NL2SQLConfig(**config)
    
    def execute(self, inputs: Dict[str, NodeInput]) -> Dict[str, NodeOutput]:
        """执行 NL2SQL 节点
        
        Args:
            inputs: 输入数据字典，包含：
                - database: {connection_string, database_info}
                - query: 用户的自然语言问题
        
        Returns:
            输出字典: {
                "data": {
                    "sql": SQL 查询,
                    "dataframe": 查询结果 DataFrame,
                    "explanation": SQL 解释
                }
            }
        """
        # 1. 提取输入
        try:
            # 从 database 端口提取连接字符串和数据库信息
            database_input = inputs["database"].data
            if not isinstance(database_input, dict):
                return self._create_error_outputs("database 输入必须是包含 connection_string 和 database_info 的字典")
            
            connection_string = database_input.get("connection_string")
            database_info = database_input.get("database_info")
            
            if not connection_string or not database_info:
                return self._create_error_outputs("database 输入必须包含 connection_string 和 database_info")
            
            # 从 query 端口提取用户问题
            user_query = inputs["query"].data
            if not isinstance(user_query, str) or not user_query.strip():
                return self._create_error_outputs("query 输入必须是非空字符串")
                
        except KeyError as e:
            return self._create_error_outputs(f"缺少必要的输入: {e}")
        except Exception as e:
            return self._create_error_outputs(f"输入解析失败: {e}")
        
        # 2. 创建数据库连接
        try:
            self.db_connection = DatabaseConnection(connection_string)
            if not self.db_connection.test_connection():
                raise ConnectionError(f"无法连接到数据库: {connection_string}")
        except Exception as e:
            return self._create_error_outputs(f"数据库连接失败: {e}")
        
        # 3. 生成 SQL（带自动修复）
        sql = None
        explanation = ""
        retries = 0
        last_error = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                if attempt == 0:
                    # 首次生成
                    if self.config.verbose:
                        print(f"[NL2SQL] 生成 SQL (attempt {attempt + 1})...")
                    
                    sql, explanation = self._generate_sql(user_query, database_info)
                else:
                    # 修复失败的 SQL
                    if self.config.verbose:
                        print(f"[NL2SQL] 修复 SQL (attempt {attempt + 1})...")
                    
                    sql, explanation = self._fix_sql(
                        user_query,
                        database_info,
                        sql,
                        str(last_error)
                    )
                
                # 4. 执行 SQL
                if self.config.verbose:
                    print(f"[NL2SQL] 执行 SQL: {sql}")
                
                result_df = self._execute_sql(sql)
                
                # 成功！
                if self.config.verbose:
                    print(f"[NL2SQL] 执行成功，返回 {len(result_df)} 行")
                
                return self._create_success_outputs(
                    sql=sql,
                    data=result_df,
                    explanation=explanation,
                    retries=attempt,
                    user_query=user_query
                )
            
            except Exception as e:
                last_error = e
                retries = attempt + 1
                
                if self.config.verbose:
                    import traceback
                    print(f"[NL2SQL] 执行失败 (attempt {attempt + 1}): {e}")
                    print(f"[NL2SQL] Traceback:")
                    traceback.print_exc()
                
                if attempt >= self.config.max_retries:
                    # 达到最大重试次数
                    break
        
        # 所有重试都失败
        return self._create_error_outputs(
            f"SQL 执行失败（尝试了 {retries} 次）: {last_error}",
            sql=sql,
            retries=retries
        )
    
    def _generate_sql(
        self,
        user_query: str,
        database_info: Dict[str, Any]
    ) -> tuple[str, str]:
        """生成 SQL 查询
        
        Args:
            user_query: 用户的自然语言问题
            database_info: 数据库信息
        
        Returns:
            (sql, explanation) 元组
        
        Raises:
            ValueError: LLM 响应格式错误
        """
        # 构建 prompt
        prompt = format_initial_prompt(user_query, database_info)
        
        # 调用 LLM
        messages = [Message(role="user", content=prompt)]
        response = self.llm_client.generate(
            messages,
            model=self.config.model,
            temperature=self.config.temperature
        )
        
        if self.config.verbose:
            print(f"[DEBUG _generate_sql] Response type: {type(response)}")
            print(f"[DEBUG _generate_sql] Response: {response}")
            if response:
                print(f"[DEBUG _generate_sql] Response content preview: {response.content[:200] if response.content else 'None'}...")
        
        # 解析响应
        parts = extract_response_parts(response.content)
        
        return parts["sql"], parts["explanation"]
    
    def _fix_sql(
        self,
        user_query: str,
        database_info: Dict[str, Any],
        previous_sql: str,
        error_message: str
    ) -> tuple[str, str]:
        """修复失败的 SQL
        
        Args:
            user_query: 用户的自然语言问题
            database_info: 数据库信息
            previous_sql: 之前失败的 SQL
            error_message: 错误信息
        
        Returns:
            (sql, explanation) 元组
        
        Raises:
            ValueError: LLM 响应格式错误
        """
        # 构建修复 prompt
        prompt = format_fix_prompt(
            user_query,
            database_info,
            previous_sql,
            error_message
        )
        
        # 调用 LLM
        messages = [Message(role="user", content=prompt)]
        response = self.llm_client.generate(
            messages,
            model=self.config.model,
            temperature=self.config.temperature
        )
        
        # 解析响应
        parts = extract_response_parts(response.content)
        
        return parts["sql"], parts["explanation"]
    
    def _execute_sql(self, sql: str) -> pd.DataFrame:
        """执行 SQL 查询
        
        Args:
            sql: SQL 查询语句
        
        Returns:
            查询结果 DataFrame
        
        Raises:
            Exception: SQL 执行错误
        """
        result_df = self.db_connection.execute_query(sql)
        
        # 应用行数限制
        if len(result_df) > self.config.max_rows:
            result_df = result_df.head(self.config.max_rows)
        
        return result_df
    
    def _create_success_outputs(
        self,
        sql: str,
        data: pd.DataFrame,
        explanation: str,
        retries: int,
        user_query: str
    ) -> Dict[str, NodeOutput]:
        """创建成功的输出
        
        Args:
            sql: SQL 查询
            data: 查询结果
            explanation: SQL 解释
            retries: 重试次数
            user_query: 用户问题
        
        Returns:
            输出字典，包含一个 data 端口，其中有 sql, dataframe, explanation
        """
        metadata = {
            "retries": retries,
            "row_count": len(data),
            "columns": list(data.columns),
            "user_query": user_query,
            "execution_time": None,  # TODO: 添加执行时间统计
        }
        
        return {
            "data": NodeOutput(
                data={
                    "sql": sql,
                    "dataframe": data,
                    "explanation": explanation
                },
                metadata=metadata,
                status="success"
            )
        }
    
    def _create_error_outputs(
        self,
        error_message: str,
        sql: Optional[str] = None,
        retries: int = 0
    ) -> Dict[str, NodeOutput]:
        """创建错误输出
        
        Args:
            error_message: 错误信息
            sql: 失败的 SQL（可选）
            retries: 重试次数
        
        Returns:
            输出字典，包含一个 data 端口，其中有 sql, dataframe, explanation
        """
        error_metadata = {
            "error": error_message,
            "retries": retries
        }
        
        return {
            "data": NodeOutput(
                data={
                    "sql": sql,
                    "dataframe": None,
                    "explanation": ""
                },
                metadata=error_metadata,
                status="failed"
            )
        }
    
    def __del__(self):
        """析构函数：关闭数据库连接"""
        if hasattr(self, 'db_connection') and self.db_connection:
            try:
                self.db_connection.close()
            except:
                pass


