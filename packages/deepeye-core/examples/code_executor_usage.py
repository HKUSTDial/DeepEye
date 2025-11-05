"""CodeExecutor使用示例

展示DataFrameCodeExecutor的各种使用场景
"""

import pandas as pd
from deepeye.runtime import BaseCodeExecutor
from deepeye.nodes.datacoder import DataFrameCodeExecutor


def example_1_basic_usage():
    """示例1：基本使用"""
    print("=" * 60)
    print("示例1：基本使用")
    print("=" * 60)
    
    # 创建测试数据
    df = pd.DataFrame({
        'name': ['Alice', 'Bob', 'Charlie', 'David'],
        'age': [25, 30, 35, 40],
        'salary': [50000, 60000, 70000, 80000]
    })
    
    print("原始数据:")
    print(df)
    print()
    
    # 创建执行器
    executor = DataFrameCodeExecutor()
    
    # 执行过滤操作
    code = "result = df[df['age'] > 28]"
    success, result_df, error = executor.execute(code, df)
    
    if success:
        print("过滤结果 (age > 28):")
        print(result_df)
    else:
        print(f"执行失败: {error}")
    print()


def example_2_complex_operations():
    """示例2：复杂数据处理"""
    print("=" * 60)
    print("示例2：复杂数据处理")
    print("=" * 60)
    
    # 创建测试数据
    df = pd.DataFrame({
        'product': ['A', 'B', 'C', 'D', 'E'],
        'sales': [100, 150, 200, 120, 180],
        'cost': [60, 80, 110, 70, 100]
    })
    
    print("原始数据:")
    print(df)
    print()
    
    executor = DataFrameCodeExecutor()
    
    # 计算利润和利润率
    code = """
# 计算利润和利润率
df['profit'] = df['sales'] - df['cost']
df['profit_margin'] = (df['profit'] / df['sales'] * 100).round(2)

# 按利润排序
result = df.sort_values('profit', ascending=False)
"""
    
    success, result_df, error = executor.execute(code, df)
    
    if success:
        print("处理结果:")
        print(result_df)
    else:
        print(f"执行失败: {error}")
    print()


def example_3_with_numpy():
    """示例3：使用NumPy进行数值计算"""
    print("=" * 60)
    print("示例3：使用NumPy进行数值计算")
    print("=" * 60)
    
    # 创建测试数据
    df = pd.DataFrame({
        'value': [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    })
    
    print("原始数据:")
    print(df)
    print()
    
    executor = DataFrameCodeExecutor()
    
    # 使用NumPy计算统计值
    code = """
import numpy as np

df['z_score'] = (df['value'] - np.mean(df['value'])) / np.std(df['value'])
df['percentile'] = df['value'].rank(pct=True) * 100

result = df
"""
    
    success, result_df, error = executor.execute(code, df)
    
    if success:
        print("处理结果:")
        print(result_df)
    else:
        print(f"执行失败: {error}")
    print()


def example_4_with_scikit_learn():
    """示例4：使用scikit-learn进行机器学习"""
    print("=" * 60)
    print("示例4：使用scikit-learn进行特征工程")
    print("=" * 60)
    
    # 创建测试数据
    df = pd.DataFrame({
        'feature1': [1, 2, 3, 4, 5],
        'feature2': [10, 20, 30, 40, 50],
        'feature3': [100, 200, 300, 400, 500]
    })
    
    print("原始数据:")
    print(df)
    print()
    
    # 包含scikit-learn库
    executor = DataFrameCodeExecutor(libraries=["pandas", "numpy", "scikit-learn"])
    
    # 标准化特征
    code = """
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
scaled_features = scaler.fit_transform(df)

result = pd.DataFrame(
    scaled_features,
    columns=[f'{col}_scaled' for col in df.columns]
)
"""
    
    success, result_df, error = executor.execute(code, df)
    
    if success:
        print("标准化结果:")
        print(result_df.round(3))
    else:
        print(f"执行失败: {error}")
    print()


def example_5_error_handling():
    """示例5：错误处理"""
    print("=" * 60)
    print("示例5：错误处理")
    print("=" * 60)
    
    df = pd.DataFrame({'a': [1, 2, 3]})
    executor = DataFrameCodeExecutor()
    
    # 测试1：缺少result变量
    print("测试1：缺少result变量")
    code1 = "x = df['a'] * 2"
    success, result_df, error = executor.execute(code1, df)
    print(f"  成功: {success}")
    print(f"  错误: {error}")
    print()
    
    # 测试2：result不是DataFrame
    print("测试2：result不是DataFrame")
    code2 = "result = df['a'].sum()"
    success, result_df, error = executor.execute(code2, df)
    print(f"  成功: {success}")
    print(f"  错误: {error}")
    print()
    
    # 测试3：语法错误
    print("测试3：语法错误")
    code3 = "result = df['a' *"
    success, result_df, error = executor.execute(code3, df)
    print(f"  成功: {success}")
    print(f"  错误: {error}")
    print()
    
    # 测试4：运行时错误
    print("测试4：运行时错误")
    code4 = "result = df['nonexistent_column']"
    success, result_df, error = executor.execute(code4, df)
    print(f"  成功: {success}")
    print(f"  错误: {error}")
    print()


def example_6_custom_executor():
    """示例6：自定义执行器"""
    print("=" * 60)
    print("示例6：自定义执行器")
    print("=" * 60)
    
    class StringProcessor(BaseCodeExecutor[str, str]):
        """字符串处理执行器"""
        
        def _prepare_code(self, code: str, text: str) -> str:
            """注入输入文本"""
            return f"""
text = '''{text}'''

# 用户代码
{code}

# 输出结果
if 'result' not in locals():
    raise ValueError("代码必须定义'result'变量")
    
if not isinstance(result, str):
    raise TypeError(f"result必须是字符串，但得到了{{type(result).__name__}}")

print("<<<RESULT_START>>>")
print(result)
print("<<<RESULT_END>>>")
"""
        
        def _extract_result(self, output: str) -> str:
            """提取结果字符串"""
            start_marker = "<<<RESULT_START>>>"
            end_marker = "<<<RESULT_END>>>"
            
            if start_marker not in output or end_marker not in output:
                raise ValueError("输出中未找到结果标记")
            
            start_idx = output.index(start_marker) + len(start_marker)
            end_idx = output.index(end_marker)
            
            return output[start_idx:end_idx].strip()
    
    # 使用自定义执行器
    executor = StringProcessor()
    
    text = "Hello, World! This is a test."
    code = """
result = text.upper().replace('HELLO', 'HI')
"""
    
    success, result_text, error = executor.execute(code, text)
    
    if success:
        print(f"原始文本: {text}")
        print(f"处理结果: {result_text}")
    else:
        print(f"执行失败: {error}")
    print()


def example_7_real_world_data_pipeline():
    """示例7：真实世界的数据处理流水线"""
    print("=" * 60)
    print("示例7：真实世界的数据处理流水线")
    print("=" * 60)
    
    # 模拟真实数据
    df = pd.DataFrame({
        'customer_id': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        'age': [25, 35, 45, 30, 50, 28, 40, 33, 37, 42],
        'purchase_amount': [100, 250, 400, 150, 500, 120, 300, 180, 280, 350],
        'purchase_count': [2, 5, 8, 3, 10, 2, 6, 4, 5, 7],
        'days_since_last_purchase': [5, 10, 3, 20, 2, 15, 7, 12, 8, 4]
    })
    
    print("原始客户数据:")
    print(df)
    print()
    
    executor = DataFrameCodeExecutor(timeout=60)
    
    # 复杂的数据处理流水线
    code = """
import numpy as np

# 1. 计算客户价值指标
df['avg_purchase'] = df['purchase_amount'] / df['purchase_count']
df['customer_value'] = df['purchase_amount'] * df['purchase_count'] / df['days_since_last_purchase']

# 2. 年龄分组
df['age_group'] = pd.cut(df['age'], bins=[0, 30, 40, 100], labels=['Young', 'Middle', 'Senior'])

# 3. 客户分级
value_quantiles = df['customer_value'].quantile([0.33, 0.67])
df['customer_tier'] = pd.cut(
    df['customer_value'],
    bins=[-np.inf, value_quantiles.iloc[0], value_quantiles.iloc[1], np.inf],
    labels=['Bronze', 'Silver', 'Gold']
)

# 4. 选择重要列并排序
result = df[[
    'customer_id', 'age', 'age_group', 'customer_tier',
    'purchase_amount', 'customer_value'
]].sort_values('customer_value', ascending=False)
"""
    
    success, result_df, error = executor.execute(code, df)
    
    if success:
        print("处理后的客户分析:")
        print(result_df)
        print()
        
        # 统计信息
        print("客户等级分布:")
        print(result_df['customer_tier'].value_counts())
        print()
        
        print("年龄组分布:")
        print(result_df['age_group'].value_counts())
    else:
        print(f"执行失败: {error}")
    print()


def main():
    """运行所有示例"""
    examples = [
        example_1_basic_usage,
        example_2_complex_operations,
        example_3_with_numpy,
        example_4_with_scikit_learn,
        example_5_error_handling,
        example_6_custom_executor,
        example_7_real_world_data_pipeline,
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"示例执行出错: {e}")
            print()


if __name__ == "__main__":
    main()

