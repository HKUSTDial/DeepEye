"""DataCoder 专用代码执行器

基于 BaseCodeExecutor 实现的 DataFrame 处理执行器
"""

from typing import Optional, Tuple, List, Union
import pandas as pd
import pickle
import base64

from deepeye.runtime.code_executor import BaseCodeExecutor

try:
    from llm_sandbox import SandboxSession
    HAS_SANDBOX = True
except ImportError:
    HAS_SANDBOX = False


class DataFrameCodeExecutor(BaseCodeExecutor[Union[pd.DataFrame, List[pd.DataFrame]], pd.DataFrame]):
    """DataFrame数据处理代码执行器
    
    专门用于DataFrame数据处理场景：
    - 输入：DataFrame（单个或多个）
    - 输出：DataFrame
    - 自动序列化/反序列化
    
    Example:
        >>> # 单DataFrame模式
        >>> executor = DataFrameCodeExecutor()
        >>> df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
        >>> code = "result = df[df['a'] > 1]"
        >>> success, result_df, error = executor.execute(code, df)
        >>> assert success
        >>> assert len(result_df) == 2
        
        >>> # 多DataFrame模式
        >>> df1 = pd.DataFrame({'id': [1, 2], 'name': ['Alice', 'Bob']})
        >>> df2 = pd.DataFrame({'id': [1, 2], 'age': [25, 30]})
        >>> code = "result = df0.merge(df1, on='id')"
        >>> success, result_df, error = executor.execute(code, [df1, df2])
        >>> assert success
        
        >>> # 使用额外的库
        >>> executor = DataFrameCodeExecutor(libraries=["pandas", "numpy", "scikit-learn"])
        >>> code = '''
        ... from sklearn.preprocessing import StandardScaler
        ... scaler = StandardScaler()
        ... df['a_scaled'] = scaler.fit_transform(df[['a']])
        ... result = df
        ... '''
        >>> success, result_df, error = executor.execute(code, df)
    """
    
    def _serialize_dataframe(self, df: pd.DataFrame) -> str:
        """序列化单个DataFrame为base64字符串
        
        Args:
            df: 要序列化的DataFrame
            
        Returns:
            base64编码的字符串
        """
        return base64.b64encode(pickle.dumps(df)).decode()
    
    def _build_dataframe_init_code(self, dataframes: List[pd.DataFrame], is_multi: bool = False) -> str:
        """构建DataFrame初始化代码
        
        Args:
            dataframes: DataFrame列表
            is_multi: 是否为多DataFrame模式
            
        Returns:
            DataFrame反序列化代码
        """
        if not is_multi and len(dataframes) == 1:
            # 单DataFrame模式：变量名为 df
            df_encoded = self._serialize_dataframe(dataframes[0])
            return f"""
# === 反序列化输入DataFrame ===
df_encoded = '''{df_encoded}'''
df = pickle.loads(base64.b64decode(df_encoded.encode()))
dataframe = df  # 提供别名
"""
        else:
            # 多DataFrame模式：变量名为 df0, df1, df2...
            init_lines = ["# === 反序列化输入DataFrames ==="]
            for i, df in enumerate(dataframes):
                df_encoded = self._serialize_dataframe(df)
                init_lines.append(f"df{i}_encoded = '''{df_encoded}'''")
                init_lines.append(f"df{i} = pickle.loads(base64.b64decode(df{i}_encoded.encode()))")
            return "\n".join(init_lines)
    
    def _prepare_code(self, code: str, context: Union[pd.DataFrame, List[pd.DataFrame]]) -> str:
        """准备代码：序列化输入DataFrame(s)
        
        Args:
            code: 用户代码
            context: 输入DataFrame（单个或列表）
            
        Returns:
            完整的可执行代码
        """
        # 判断是单DataFrame还是多DataFrame模式
        if isinstance(context, list):
            # 多DataFrame模式
            dataframes = context
            is_multi = True
        else:
            # 单DataFrame模式
            dataframes = [context]
            is_multi = False
        
        # 使用辅助方法构建DataFrame初始化代码
        df_init_code = self._build_dataframe_init_code(dataframes, is_multi)
        
        # 构建完整代码
        full_code = f"""
import pandas as pd
import numpy as np
import pickle
import base64

{df_init_code}

# === 用户代码 ===
{code}

# === 验证和序列化输出 ===
if 'result' not in locals():
    raise ValueError("代码必须定义'result'变量")

if not isinstance(result, pd.DataFrame):
    raise TypeError(f"result必须是DataFrame，但得到了{{type(result).__name__}}")

result_encoded = base64.b64encode(pickle.dumps(result)).decode()
print("<<<DATAFRAME_START>>>")
print(result_encoded)
print("<<<DATAFRAME_END>>>")
"""
        return full_code
    
    def _extract_result(self, output: str) -> pd.DataFrame:
        """从输出中提取DataFrame"""
        start_marker = "<<<DATAFRAME_START>>>"
        end_marker = "<<<DATAFRAME_END>>>"
        
        if start_marker not in output or end_marker not in output:
            raise ValueError(
                f"输出中未找到DataFrame标记\n"
                f"输出内容: {output[:500]}..."
            )
        
        start_idx = output.index(start_marker) + len(start_marker)
        end_idx = output.index(end_marker)
        
        encoded = output[start_idx:end_idx].strip()
        return pickle.loads(base64.b64decode(encoded.encode()))

