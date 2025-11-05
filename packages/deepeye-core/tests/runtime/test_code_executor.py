"""测试CodeExecutor - 基于llm-sandbox的沙盒代码执行器

测试覆盖：
1. 基础执行功能
2. DataFrame专用执行器
3. 自定义执行器扩展
4. 错误处理
5. 真实场景
"""

import pytest
import pandas as pd
import numpy as np
from typing import Optional, List

from deepeye.runtime.code_executor import (
    BaseCodeExecutor,
    HAS_SANDBOX
)
from deepeye.nodes.datacoder.executor import DataFrameCodeExecutor


# ============================================================================
# 测试前置条件
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def check_sandbox():
    """检查llm-sandbox是否安装"""
    if not HAS_SANDBOX:
        pytest.skip(
            "需要安装llm-sandbox才能运行代码执行器测试:\n"
            "  uv pip install 'llm-sandbox[docker]'\n"
            "  或: pip install 'llm-sandbox[docker]'"
        )


@pytest.fixture
def sample_dataframe():
    """示例DataFrame"""
    return pd.DataFrame({
        'name': ['Alice', 'Bob', 'Charlie', 'David'],
        'age': [25, 30, 28, 35],
        'salary': [50000, 60000, 55000, 70000],
        'department': ['HR', 'IT', 'IT', 'HR']
    })


# ============================================================================
# 自定义执行器示例（用于测试扩展性）
# ============================================================================

class SimpleExecutor(BaseCodeExecutor[dict, int]):
    """简单的字典->整数执行器
    
    输入：字典上下文
    输出：整数结果
    """
    
    def _prepare_code(self, code: str, context: dict) -> str:
        """注入字典变量"""
        # 构建变量定义
        var_defs = "\n".join(f"{k} = {repr(v)}" for k, v in context.items())
        
        return f"""
{var_defs}

# 用户代码
{code}

# 输出结果
print("<<<RESULT_START>>>")
print(result)
print("<<<RESULT_END>>>")
"""
    
    def _extract_result(self, output: str) -> int:
        """提取整数结果"""
        start = output.index("<<<RESULT_START>>>") + len("<<<RESULT_START>>>")
        end = output.index("<<<RESULT_END>>>")
        result_str = output[start:end].strip()
        return int(result_str)


class StringExecutor(BaseCodeExecutor[str, str]):
    """字符串处理执行器
    
    输入：字符串
    输出：字符串
    """
    
    def _prepare_code(self, code: str, context: str) -> str:
        """注入字符串变量"""
        return f"""
text = {repr(context)}

# 用户代码
{code}

# 输出结果
print("<<<OUTPUT_START>>>")
print(result)
print("<<<OUTPUT_END>>>")
"""
    
    def _extract_result(self, output: str) -> str:
        """提取字符串结果"""
        start = output.index("<<<OUTPUT_START>>>") + len("<<<OUTPUT_START>>>")
        end = output.index("<<<OUTPUT_END>>>")
        return output[start:end].strip()


# ============================================================================
# 测试 DataFrameCodeExecutor
# ============================================================================

class TestDataFrameCodeExecutor:
    """测试DataFrame代码执行器"""
    
    def test_init_default(self):
        """测试默认初始化"""
        executor = DataFrameCodeExecutor()
        
        assert executor.timeout == 30
        assert executor.libraries == []  # 默认为空，pandas/numpy 在代码模板中导入
        assert executor.verbose is False
    
    def test_init_custom(self):
        """测试自定义参数初始化"""
        executor = DataFrameCodeExecutor(
            timeout=60,
            libraries=["scikit-learn"],
            verbose=True
        )
        
        assert executor.timeout == 60
        assert "scikit-learn" in executor.libraries
        assert executor.verbose is True
    
    def test_execute_simple_filter(self, sample_dataframe):
        """测试简单过滤操作"""
        executor = DataFrameCodeExecutor()
        
        code = "result = df[df['age'] > 28]"
        success, result_df, error = executor.execute(code, sample_dataframe)
        
        assert success, f"执行失败: {error}"
        assert error is None
        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == 2  # Bob(30) 和 David(35)
        assert list(result_df['name']) == ['Bob', 'David']
    
    def test_execute_column_selection(self, sample_dataframe):
        """测试列选择"""
        executor = DataFrameCodeExecutor()
        
        code = "result = df[['name', 'age']]"
        success, result_df, error = executor.execute(code, sample_dataframe)
        
        assert success
        assert list(result_df.columns) == ['name', 'age']
        assert len(result_df) == 4
    
    def test_execute_aggregation(self, sample_dataframe):
        """测试聚合操作"""
        executor = DataFrameCodeExecutor()
        
        code = """
result = df.groupby('department').agg({
    'salary': 'mean',
    'age': 'mean'
}).reset_index()
"""
        success, result_df, error = executor.execute(code, sample_dataframe)
        
        assert success, f"执行失败: {error}"
        assert len(result_df) == 2  # HR 和 IT
        assert 'department' in result_df.columns
        assert 'salary' in result_df.columns
    
    def test_execute_new_column(self, sample_dataframe):
        """测试添加新列"""
        executor = DataFrameCodeExecutor()
        
        code = """
result = df.copy()
result['salary_k'] = result['salary'] / 1000
result['is_senior'] = result['age'] >= 30
"""
        success, result_df, error = executor.execute(code, sample_dataframe)
        
        assert success
        assert 'salary_k' in result_df.columns
        assert 'is_senior' in result_df.columns
        assert result_df['salary_k'].iloc[0] == 50.0
    
    def test_execute_sorting(self, sample_dataframe):
        """测试排序"""
        executor = DataFrameCodeExecutor()
        
        code = "result = df.sort_values('salary', ascending=False)"
        success, result_df, error = executor.execute(code, sample_dataframe)
        
        assert success
        assert result_df['salary'].iloc[0] == 70000  # David
        assert result_df['name'].iloc[0] == 'David'
    
    def test_execute_multiline_complex(self, sample_dataframe):
        """测试复杂多行代码"""
        executor = DataFrameCodeExecutor()
        
        code = """
# 1. 过滤
filtered = df[df['age'] > 25]

# 2. 计算新列
filtered = filtered.copy()
filtered['bonus'] = filtered['salary'] * 0.1

# 3. 选择列
result = filtered[['name', 'salary', 'bonus']]
"""
        success, result_df, error = executor.execute(code, sample_dataframe)
        
        assert success, f"执行失败: {error}"
        assert len(result_df) == 3  # Bob, Charlie, David
        assert 'bonus' in result_df.columns
    
    def test_execute_with_numpy(self, sample_dataframe):
        """测试使用numpy"""
        executor = DataFrameCodeExecutor()
        
        code = """
result = df.copy()
result['salary_normalized'] = (
    (result['salary'] - result['salary'].mean()) / 
    np.std(result['salary'])
)
"""
        success, result_df, error = executor.execute(code, sample_dataframe)
        
        assert success, f"执行失败: {error}"
        assert 'salary_normalized' in result_df.columns
        # 标准化后均值应接近0
        assert abs(result_df['salary_normalized'].mean()) < 1e-10
    
    def test_execute_dataframe_alias(self):
        """测试dataframe别名"""
        executor = DataFrameCodeExecutor()
        
        df = pd.DataFrame({'x': [1, 2, 3]})
        
        # 使用dataframe别名而不是df
        code = "result = dataframe[dataframe['x'] > 1]"
        success, result_df, error = executor.execute(code, df)
        
        assert success
        assert len(result_df) == 2
    
    def test_execute_empty_dataframe(self):
        """测试空DataFrame"""
        executor = DataFrameCodeExecutor()
        
        df = pd.DataFrame({'a': []})
        code = "result = df"
        
        success, result_df, error = executor.execute(code, df)
        
        assert success
        assert len(result_df) == 0
    
    def test_execute_with_additional_libraries(self, sample_dataframe):
        """测试使用额外的库"""
        executor = DataFrameCodeExecutor()
        
        code = """
from datetime import datetime
result = df.copy()
result['processed_at'] = datetime.now().strftime('%Y-%m-%d')
"""
        success, result_df, error = executor.execute(
            code,
            sample_dataframe,
            additional_libraries=[]  # datetime是标准库，不需要安装
        )
        
        assert success, f"执行失败: {error}"
        assert 'processed_at' in result_df.columns


class TestDataFrameCodeExecutorErrors:
    """测试DataFrame执行器错误处理"""
    
    def test_no_result_variable(self, sample_dataframe):
        """测试缺少result变量"""
        executor = DataFrameCodeExecutor()
        
        code = "df_filtered = df[df['age'] > 30]"  # 没有定义result
        success, result, error = executor.execute(code, sample_dataframe)
        
        assert not success
        assert result is None
        assert "result" in error.lower()
    
    def test_result_not_dataframe(self, sample_dataframe):
        """测试result不是DataFrame"""
        executor = DataFrameCodeExecutor()
        
        code = "result = df['age'].sum()"  # result是整数
        success, result, error = executor.execute(code, sample_dataframe)
        
        assert not success
        assert result is None
        assert "DataFrame" in error
    
    def test_syntax_error(self, sample_dataframe):
        """测试语法错误"""
        executor = DataFrameCodeExecutor()
        
        code = "result = df[df['age'] >"  # 语法错误
        success, result, error = executor.execute(code, sample_dataframe)
        
        assert not success
        assert result is None
        assert error is not None
    
    def test_runtime_error(self, sample_dataframe):
        """测试运行时错误"""
        executor = DataFrameCodeExecutor()
        
        code = "result = df[df['nonexistent_column'] > 0]"
        success, result, error = executor.execute(code, sample_dataframe)
        
        assert not success
        assert "KeyError" in error or "nonexistent_column" in error
    
    def test_type_error(self, sample_dataframe):
        """测试类型错误"""
        executor = DataFrameCodeExecutor()
        
        code = "result = df['name'] + 100"  # 字符串+整数
        success, result, error = executor.execute(code, sample_dataframe)
        
        assert not success
        assert result is None


# ============================================================================
# 测试自定义执行器
# ============================================================================

class TestCustomExecutors:
    """测试自定义执行器"""
    
    def test_simple_executor(self):
        """测试SimpleExecutor"""
        executor = SimpleExecutor()
        
        code = "result = x + y * 2"
        success, result, error = executor.execute(code, {'x': 10, 'y': 20})
        
        assert success, f"执行失败: {error}"
        assert result == 50
    
    def test_simple_executor_complex(self):
        """测试SimpleExecutor复杂计算"""
        executor = SimpleExecutor()
        
        code = """
total = 0
for i in range(start, end):
    total += i
result = total
"""
        success, result, error = executor.execute(code, {'start': 1, 'end': 11})
        
        assert success
        assert result == 55  # 1+2+...+10
    
    def test_string_executor(self):
        """测试StringExecutor"""
        executor = StringExecutor()
        
        code = "result = text.upper()"
        success, result, error = executor.execute(code, "hello world")
        
        assert success, f"执行失败: {error}"
        assert result == "HELLO WORLD"
    
    def test_string_executor_complex(self):
        """测试StringExecutor复杂处理"""
        executor = StringExecutor()
        
        code = """
words = text.split()
result = '-'.join(word.capitalize() for word in words)
"""
        success, result, error = executor.execute(code, "hello world python")
        
        assert success
        assert result == "Hello-World-Python"


# ============================================================================
# 测试BaseCodeExecutor抽象类
# ============================================================================

class TestBaseCodeExecutor:
    """测试BaseCodeExecutor基类"""
    
    def test_cannot_instantiate(self):
        """测试不能直接实例化抽象类"""
        with pytest.raises(TypeError):
            BaseCodeExecutor()
    
    def test_custom_timeout(self):
        """测试自定义超时"""
        executor = SimpleExecutor(timeout=60)
        assert executor.timeout == 60
    
    def test_custom_libraries(self):
        """测试自定义库列表"""
        executor = SimpleExecutor(libraries=["requests", "beautifulsoup4"])
        assert "requests" in executor.libraries
        assert "beautifulsoup4" in executor.libraries
    
    def test_global_container_reuse(self):
        """测试全局容器复用（替代 keep_template）"""
        executor = SimpleExecutor()
        
        # 执行两次代码 - 全局容器会自动复用
        code1 = "result = x * 2"
        success1, result1, error1 = executor.execute(code1, {'x': 5})
        
        code2 = "result = y + 10"
        success2, result2, error2 = executor.execute(code2, {'y': 3})
        
        assert success1 and success2, f"执行失败: error1={error1}, error2={error2}"
        assert result1 == 10
        assert result2 == 13


# ============================================================================
# 测试真实场景
# ============================================================================

class TestRealWorldScenarios:
    """测试真实世界场景"""
    
    def test_data_cleaning(self):
        """测试数据清洗"""
        executor = DataFrameCodeExecutor()
        
        df = pd.DataFrame({
            'name': ['Alice', 'Bob', None, 'David', 'Eve'],
            'age': [25, None, 28, 35, 30],
            'salary': [50000, 60000, None, 70000, 65000],
            'email': ['a@x.com', 'invalid', 'c@x.com', 'd@x.com', 'e@x.com']
        })
        
        code = """
# 1. 删除缺失值
cleaned = df.dropna()

# 2. 过滤有效邮箱
cleaned = cleaned[cleaned['email'].str.contains('@')]

result = cleaned
"""
        success, result_df, error = executor.execute(code, df)
        
        assert success, f"执行失败: {error}"
        assert len(result_df) == 3  # Alice, David, Eve
    
    def test_feature_engineering(self):
        """测试特征工程"""
        executor = DataFrameCodeExecutor()
        
        df = pd.DataFrame({
            'age': [22, 28, 35, 45, 50],
            'income': [30000, 50000, 70000, 90000, 100000],
            'experience': [1, 5, 10, 20, 25]
        })
        
        code = """
result = df.copy()

# 分组特征
result['age_group'] = pd.cut(
    result['age'], 
    bins=[0, 30, 40, 100], 
    labels=['young', 'middle', 'senior']
)

# 比例特征
result['income_per_exp'] = result['income'] / (result['experience'] + 1)

# 对数特征
result['log_income'] = np.log(result['income'])
"""
        success, result_df, error = executor.execute(code, df)
        
        assert success, f"执行失败: {error}"
        assert 'age_group' in result_df.columns
        assert 'income_per_exp' in result_df.columns
        assert 'log_income' in result_df.columns
    
    def test_statistical_analysis(self):
        """测试统计分析"""
        executor = DataFrameCodeExecutor()
        
        df = pd.DataFrame({
            'category': ['A', 'A', 'B', 'B', 'C', 'C'],
            'value': [10, 15, 20, 25, 30, 35]
        })
        
        code = """
result = df.groupby('category')['value'].agg([
    ('mean', 'mean'),
    ('std', 'std'),
    ('min', 'min'),
    ('max', 'max'),
    ('count', 'count')
]).reset_index()
"""
        success, result_df, error = executor.execute(code, df)
        
        assert success, f"执行失败: {error}"
        assert len(result_df) == 3
        assert all(col in result_df.columns for col in ['mean', 'std', 'min', 'max', 'count'])
    
    def test_data_transformation(self):
        """测试数据转换"""
        executor = DataFrameCodeExecutor()
        
        df = pd.DataFrame({
            'date': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'value': [100, 150, 120]
        })
        
        code = """
result = df.copy()
result['date'] = pd.to_datetime(result['date'])
result['day_of_week'] = result['date'].dt.day_name()
result['value_change'] = result['value'].pct_change() * 100
"""
        success, result_df, error = executor.execute(code, df)
        
        assert success, f"执行失败: {error}"
        assert 'day_of_week' in result_df.columns
        assert 'value_change' in result_df.columns
    
    def test_outlier_detection(self):
        """测试异常值检测"""
        executor = DataFrameCodeExecutor()
        
        df = pd.DataFrame({
            'value': [10, 12, 11, 13, 100, 12, 14, 11]  # 100是异常值
        })
        
        code = """
# 使用IQR方法检测异常值
Q1 = df['value'].quantile(0.25)
Q3 = df['value'].quantile(0.75)
IQR = Q3 - Q1

lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR

result = df[
    (df['value'] >= lower_bound) & 
    (df['value'] <= upper_bound)
]
"""
        success, result_df, error = executor.execute(code, df)
        
        assert success, f"执行失败: {error}"
        assert len(result_df) == 7  # 移除了100
        assert 100 not in result_df['value'].values


# ============================================================================
# 测试边界情况
# ============================================================================

class TestEdgeCases:
    """测试边界情况"""
    
    def test_large_dataframe(self):
        """测试大DataFrame"""
        executor = DataFrameCodeExecutor()
        
        # 创建10000行的DataFrame
        df = pd.DataFrame({
            'id': range(10000),
            'value': np.random.randn(10000)
        })
        
        code = "result = df[df['value'] > 0]"
        success, result_df, error = executor.execute(code, df)
        
        assert success, f"执行失败: {error}"
        assert len(result_df) > 0
    
    def test_unicode_data(self):
        """测试Unicode数据"""
        executor = DataFrameCodeExecutor()
        
        df = pd.DataFrame({
            'name': ['张三', '李四', 'Wang Wu'],
            'city': ['北京', '上海', 'Shenzhen']
        })
        
        code = "result = df[df['name'].str.contains('张')]"
        success, result_df, error = executor.execute(code, df)
        
        assert success, f"执行失败: {error}"
        assert len(result_df) == 1
        assert result_df['name'].iloc[0] == '张三'
    
    def test_special_column_names(self):
        """测试特殊列名"""
        executor = DataFrameCodeExecutor()
        
        df = pd.DataFrame({
            'column with spaces': [1, 2, 3],
            'column-with-dashes': [4, 5, 6],
            'column.with.dots': [7, 8, 9]
        })
        
        code = "result = df[['column with spaces', 'column-with-dashes']]"
        success, result_df, error = executor.execute(code, df)
        
        assert success, f"执行失败: {error}"
        assert len(result_df.columns) == 2
    
    def test_mixed_types(self):
        """测试混合类型"""
        executor = DataFrameCodeExecutor()
        
        df = pd.DataFrame({
            'int_col': [1, 2, 3],
            'float_col': [1.5, 2.5, 3.5],
            'str_col': ['a', 'b', 'c'],
            'bool_col': [True, False, True]
        })
        
        code = "result = df[df['bool_col']]"
        success, result_df, error = executor.execute(code, df)
        
        assert success
        assert len(result_df) == 2
    
    def test_code_with_comments(self):
        """测试带注释的代码"""
        executor = DataFrameCodeExecutor()
        
        df = pd.DataFrame({'x': [1, 2, 3]})
        
        code = """
# 这是注释
result = df  # 行内注释

# 多行注释
# 继续注释
"""
        success, result_df, error = executor.execute(code, df)
        
        assert success
        assert len(result_df) == 3


# ============================================================================
# 性能和可靠性测试
# ============================================================================

class TestPerformanceAndReliability:
    """测试性能和可靠性"""
    
    def test_multiple_executions(self):
        """测试多次执行（使用全局容器）"""
        executor = DataFrameCodeExecutor()
        
        df = pd.DataFrame({'x': [1, 2, 3]})
        code = "result = df"
        
        # 执行多次
        for _ in range(3):
            success, result_df, error = executor.execute(code, df)
            assert success, f"执行失败: {error}"
            assert len(result_df) == 3
    
    def test_different_dataframes(self):
        """测试处理不同的DataFrame"""
        executor = DataFrameCodeExecutor()
        
        # DataFrame 1
        df1 = pd.DataFrame({'a': [1, 2]})
        success, result1, error = executor.execute("result = df", df1)
        assert success
        assert len(result1) == 2
        
        # DataFrame 2
        df2 = pd.DataFrame({'b': [1, 2, 3, 4]})
        success, result2, error = executor.execute("result = df", df2)
        assert success
        assert len(result2) == 4


# ============================================================================
# 集成测试
# ============================================================================

class TestIntegration:
    """集成测试"""
    
    def test_end_to_end_data_pipeline(self):
        """测试端到端数据管道"""
        executor = DataFrameCodeExecutor()
        
        # 原始数据
        raw_df = pd.DataFrame({
            'name': ['Alice', 'Bob', None, 'David', 'Eve'],
            'age': [25, 30, 28, 35, 30],
            'salary': [50000, 60000, 55000, 70000, None],
            'department': ['HR', 'IT', 'IT', 'HR', 'IT']
        })
        
        # 步骤1: 清洗数据
        clean_code = """
result = df.dropna()
"""
        success, clean_df, error = executor.execute(clean_code, raw_df)
        assert success
        
        # 步骤2: 特征工程
        feature_code = """
result = df.copy()
result['salary_k'] = result['salary'] / 1000
result['is_senior'] = result['age'] >= 30
"""
        success, feature_df, error = executor.execute(feature_code, clean_df)
        assert success
        
        # 步骤3: 聚合统计
        agg_code = """
result = df.groupby('department').agg({
    'salary': 'mean',
    'age': 'mean'
}).reset_index()
"""
        success, final_df, error = executor.execute(agg_code, feature_df)
        assert success
        
        # 验证最终结果
        assert len(final_df) == 2  # HR 和 IT
        assert 'department' in final_df.columns
