"""NL2SQL 完整示例

演示如何使用 DatabaseDataSourceNode 和 NL2SQLNode 进行自然语言数据库查询。

场景：
1. 内省模式 + NL2SQL：自然语言查询数据库
2. 直接查询模式：执行已知的 SQL
3. 完整分析流程：NL2SQL → DataCoder → DataPlot
4. Schema 详细内省

环境变量配置：
- OPENAI_API_KEY: OpenAI API Key（必需）
- OPENAI_BASE_URL: OpenAI API Base URL（可选，默认为官方地址）
- OPENAI_MODEL: 使用的模型（可选，默认 gpt-4）
"""

import os
import sys
import sqlite3
import pandas as pd

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from deepeye.nodes.database import DatabaseDataSourceNode
from deepeye.nodes.nl2sql import NL2SQLNode
from deepeye.nodes.datacoder import DataCoderNode
from deepeye.nodes.dataplot import DataPlotNode
from deepeye.nodes.io import NodeInput


# ============================================================================
# 准备测试数据库
# ============================================================================

def create_sample_database(db_path: str = "sales_data.db"):
    """创建示例销售数据库
    
    包含三个表：
    - products: 产品信息
    - customers: 客户信息
    - orders: 订单信息
    """
    # 删除旧数据库
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # 创建连接
    conn = sqlite3.connect(db_path)
    
    # 创建 products 表
    conn.execute("""
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL
        )
    """)
    
    # 插入产品数据
    products = [
        (1, "Laptop Pro", "Electronics", 1299.99, 50),
        (2, "Wireless Mouse", "Electronics", 29.99, 200),
        (3, "Office Chair", "Furniture", 199.99, 30),
        (4, "Standing Desk", "Furniture", 499.99, 15),
        (5, "USB-C Cable", "Accessories", 12.99, 500),
        (6, "Monitor 27''", "Electronics", 349.99, 40),
        (7, "Keyboard Mechanical", "Electronics", 89.99, 100),
        (8, "Desk Lamp", "Furniture", 45.99, 80),
        (9, "Notebook Set", "Stationery", 15.99, 300),
        (10, "Pen Pack", "Stationery", 5.99, 500),
    ]
    conn.executemany(
        "INSERT INTO products VALUES (?, ?, ?, ?, ?)",
        products
    )
    
    # 创建 customers 表
    conn.execute("""
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            customer_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            city TEXT NOT NULL,
            registration_date DATE NOT NULL
        )
    """)
    
    # 插入客户数据
    customers = [
        (1, "Alice Smith", "alice@example.com", "New York", "2023-01-15"),
        (2, "Bob Johnson", "bob@example.com", "Los Angeles", "2023-02-20"),
        (3, "Charlie Brown", "charlie@example.com", "Chicago", "2023-03-10"),
        (4, "Diana Prince", "diana@example.com", "Houston", "2023-04-05"),
        (5, "Eve Wilson", "eve@example.com", "Phoenix", "2023-05-12"),
    ]
    conn.executemany(
        "INSERT INTO customers VALUES (?, ?, ?, ?, ?)",
        customers
    )
    
    # 创建 orders 表
    conn.execute("""
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            order_date DATE NOT NULL,
            total_amount REAL NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)
    
    # 插入订单数据
    orders = [
        (1, 1, 1, 1, "2024-01-10", 1299.99),
        (2, 1, 2, 2, "2024-01-10", 59.98),
        (3, 2, 3, 1, "2024-01-15", 199.99),
        (4, 2, 6, 1, "2024-01-15", 349.99),
        (5, 3, 5, 5, "2024-02-01", 64.95),
        (6, 3, 10, 10, "2024-02-01", 59.90),
        (7, 4, 4, 1, "2024-02-10", 499.99),
        (8, 4, 8, 2, "2024-02-10", 91.98),
        (9, 5, 7, 1, "2024-03-01", 89.99),
        (10, 5, 9, 3, "2024-03-01", 47.97),
        (11, 1, 6, 2, "2024-03-15", 699.98),
        (12, 2, 1, 1, "2024-04-01", 1299.99),
    ]
    conn.executemany(
        "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)",
        orders
    )
    
    conn.commit()
    conn.close()
    
    print(f"✅ 创建示例数据库: {db_path}")
    print("   - 10 个产品")
    print("   - 5 个客户")
    print("   - 12 个订单")
    print()


# ============================================================================
# 场景 1: 内省模式 + NL2SQL
# ============================================================================

def example_1_nl2sql_basic():
    """场景 1: 基础 NL2SQL 查询"""
    print("=" * 80)
    print("场景 1: 基础 NL2SQL 查询")
    print("=" * 80)
    print()
    
    # 检查是否设置了 API Key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  未设置 OPENAI_API_KEY 环境变量，跳过 NL2SQL 测试")
        print("   提示: export OPENAI_API_KEY='your-api-key'")
        return
    
    # Step 1: 内省数据库
    print("Step 1: 内省数据库...")
    db_source = DatabaseDataSourceNode(
        node_id="db_introspect",
        config={
            "connection_string": "sqlite:///sales_data.db",
            "sample_size": 3,  # 每个表采样 3 行
            "include_statistics": True
        }
    )
    
    introspect_outputs = db_source.run(inputs={})
    
    if introspect_outputs["data"].status != "success":
        print("❌ 数据库内省失败")
        return
    
    print("✅ 数据库内省成功")
    db_data = introspect_outputs["data"].data
    db_info = db_data["database_info"]
    print(f"   - 发现 {len(db_info['schema']['tables'])} 个表: {db_info['schema']['tables']}")
    print()
    
    # Step 2: NL2SQL 查询
    print("Step 2: NL2SQL 查询...")
    
    # 从环境变量读取配置
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-4o")
    
    nl2sql_node = NL2SQLNode(
        node_id="nl2sql",
        config={
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
            "temperature": 0.0,
            "max_retries": 3,
            "verbose": True
        }
    )
    
    # 测试几个自然语言问题
    queries = [
        "找出销售额最高的 5 个产品",
        "哪些客户在 2024 年 2 月有购买记录？",
        "计算每个类别的平均产品价格",
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n问题 {i}: {query}")
        print("-" * 80)
        
        # 新的输入格式：database 端口包含 connection_string 和 database_info
        nl2sql_outputs = nl2sql_node.run({
            "database": NodeInput(data={
                "connection_string": db_data["connection_string"],
                "database_info": db_info
            }),
            "query": NodeInput(data=query)
        })
        
        # 新的输出格式：只有一个 data 端口，包含 sql、dataframe 和 explanation
        if nl2sql_outputs["data"].status == "success":
            result = nl2sql_outputs["data"].data
            sql = result["sql"]
            dataframe = result["dataframe"]
            explanation = result["explanation"]
            retries = nl2sql_outputs["data"].metadata.get("retries", 0)
            
            print(f"✅ 查询成功（重试次数: {retries}）")
            print(f"\n生成的 SQL:")
            print(f"```sql")
            print(sql)
            print(f"```")
            print(f"\n解释: {explanation}")
            print(f"\n结果 ({len(dataframe)} 行):")
            print(dataframe.to_string())
        else:
            error_msg = nl2sql_outputs["data"].error or "未知错误"
            print(f"❌ 查询失败: {error_msg}")
    
    print()


# ============================================================================
# 场景 2: 直接查询模式
# ============================================================================

def example_2_direct_query():
    """场景 2: 直接 SQL 查询"""
    print("=" * 80)
    print("场景 2: 直接 SQL 查询")
    print("=" * 80)
    print()
    
    # 直接查询模式（通过 inputs 提供 SQL）
    db_query = DatabaseDataSourceNode(
        node_id="db_query",
        config={
            "connection_string": "sqlite:///sales_data.db",
            "mode": "query"  # 设置为查询模式
        }
    )
    
    # 通过 inputs 传递 SQL
    outputs = db_query.run(inputs={
        "sql": NodeInput(data="""
            SELECT 
                p.product_name,
                p.category,
                SUM(o.total_amount) as total_sales,
                COUNT(o.order_id) as order_count
            FROM products p
            JOIN orders o ON p.product_id = o.product_id
            GROUP BY p.product_id, p.product_name, p.category
            ORDER BY total_sales DESC
            LIMIT 5
        """)
    })
    
    if outputs["data"].status == "success":
        result = outputs["data"].data
        df = result["dataframe"]  # 查询模式下，data 包含 dataframe 键
        print("✅ 查询成功")
        print("\n销售额 TOP 5 产品:")
        print(df.to_string())
    else:
        error_msg = outputs["data"].error or "未知错误"
        print(f"❌ 查询失败: {error_msg}")
    
    print()


# ============================================================================
# 场景 3: 完整分析流程
# ============================================================================

def example_3_complete_pipeline():
    """场景 3: NL2SQL → DataCoder → DataPlot 完整流程"""
    print("=" * 80)
    print("场景 3: 完整分析流程（NL2SQL → DataCoder → DataPlot）")
    print("=" * 80)
    print()
    
    # 检查 API Key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  未设置 OPENAI_API_KEY 环境变量，跳过完整流程测试")
        return
    
    # 从环境变量读取配置
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-4o")
    
    # Step 1: 内省数据库
    print("Step 1: 内省数据库...")
    db_source = DatabaseDataSourceNode(
        node_id="db_introspect",
        config={
            "connection_string": "sqlite:///sales_data.db",
            "sample_size": 5
        }
    )
    introspect_outputs = db_source.run(inputs={})
    
    if introspect_outputs["data"].status != "success":
        print("❌ 数据库内省失败")
        return
    
    print("✅ 内省完成\n")
    db_data = introspect_outputs["data"].data
    db_info = db_data["database_info"]
    
    # Step 2: NL2SQL 查询
    print("Step 2: NL2SQL 查询...")
    nl2sql_node = NL2SQLNode(
        node_id="nl2sql",
        config={
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
            "verbose": True
        }
    )
    
    nl2sql_outputs = nl2sql_node.run({
        "database": NodeInput(data={
            "connection_string": db_data["connection_string"],
            "database_info": db_info
        }),
        "query": NodeInput(data="查询每个月的总销售额和订单数量")
    })
    
    if nl2sql_outputs["data"].status != "success":
        error_msg = nl2sql_outputs["data"].error or "未知错误"
        print(f"❌ NL2SQL 失败: {error_msg}")
        return
    
    print("✅ NL2SQL 完成")
    nl2sql_result = nl2sql_outputs["data"].data
    print(f"\n生成的 SQL:\n{nl2sql_result['sql']}")
    print(f"\n原始结果:")
    print(nl2sql_result["dataframe"].to_string())
    print()
    
    # Step 3: DataCoder 数据处理
    print("Step 3: DataCoder 数据处理...")
    datacoder_node = DataCoderNode(
        node_id="datacoder",
        config={
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
            "verbose": True
        }
    )
    
    # DataCoder 接收 DataFrame，需要从 nl2sql_result 中提取
    datacoder_outputs = datacoder_node.run({
        "data": NodeInput(data={"dataframe": nl2sql_result["dataframe"]}),
        "task": NodeInput(data={"description": "添加一列显示环比增长率"})
    })
    
    if datacoder_outputs["result"].status != "success":
        error_msg = datacoder_outputs["result"].error or "未知错误"
        print(f"❌ DataCoder 失败: {error_msg}")
        return
    
    print("✅ DataCoder 完成")
    datacoder_result = datacoder_outputs["result"].data
    print(f"\n处理后的数据:")
    print(datacoder_result["dataframe"].to_string())
    print()
    
    # Step 4: DataPlot 可视化
    print("Step 4: DataPlot 可视化...")
    dataplot_node = DataPlotNode(
        node_id="dataplot",
        config={
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
            "verbose": True
        }
    )
    
    dataplot_outputs = dataplot_node.run({
        "data": NodeInput(data={"dataframe": datacoder_result["dataframe"]}),
        "task": NodeInput(data={"description": "画一个折线图展示每月销售额的变化趋势"})
    })
    
    if dataplot_outputs["images"].status == "success":
        images = dataplot_outputs["images"].data
        print("✅ DataPlot 完成")
        print(f"   生成了 {len(images)} 个图片")
        
        # 保存第一个图片
        if images:
            output_path = "monthly_sales_trend.png"
            with open(output_path, "wb") as f:
                f.write(images[0]["data"])
            print(f"   图表已保存到: {output_path}")
    else:
        error_msg = dataplot_outputs["data"].error or "未知错误"
        print(f"❌ DataPlot 失败: {error_msg}")
    
    print()


# ============================================================================
# 场景 4: Schema 展示
# ============================================================================

def example_4_schema_inspection():
    """场景 4: 详细的 Schema 内省"""
    print("=" * 80)
    print("场景 4: 详细的 Schema 内省")
    print("=" * 80)
    print()
    
    db_source = DatabaseDataSourceNode(
        node_id="db_introspect",
        config={
            "connection_string": "sqlite:///sales_data.db",
            "sample_size": 3,
            "include_statistics": True
        }
    )
    
    outputs = db_source.run(inputs={})
    
    if outputs["data"].status != "success":
        print("❌ 内省失败")
        return
    
    db_data = outputs["data"].data
    db_info = db_data["database_info"]
    schema = db_info["schema"]
    examples = db_info["examples"]
    statistics = db_info["statistics"]
    
    # 显示每个表的详细信息
    for table in schema["tables"]:
        print(f"\n📊 Table: {table}")
        print("=" * 60)
        
        # 列信息
        print("\n列信息:")
        for col in schema["columns"][table]:
            nullable = "NULL" if col["nullable"] else "NOT NULL"
            print(f"  - {col['name']:20s} {col['type']:15s} {nullable}")
        
        # 主键
        if schema["primary_keys"][table]:
            print(f"\n主键: {', '.join(schema['primary_keys'][table])}")
        
        # 外键
        if schema["foreign_keys"][table]:
            print("\n外键:")
            for fk in schema["foreign_keys"][table]:
                print(f"  - {', '.join(fk['constrained_columns'])} → "
                      f"{fk['referred_table']}({', '.join(fk['referred_columns'])})")
        
        # 统计信息
        if table in statistics:
            stats = statistics[table]
            print(f"\n统计信息:")
            print(f"  - 总行数: {stats['row_count']:,}")
            print(f"  - 列数: {len(schema['columns'][table])}")
        
        # 示例数据
        if table in examples and not isinstance(examples[table], dict) or "error" not in examples[table]:
            print("\n示例数据 (前 3 行):")
            df_sample = pd.DataFrame(examples[table])
            print(df_sample.to_string(index=False))
    
    print()


# ============================================================================
# 环境变量配置说明
# ============================================================================

def print_environment_info():
    """打印环境变量配置信息"""
    print("📋 环境变量配置:")
    print("-" * 80)
    
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-4o")
    
    if api_key:
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        print(f"  ✅ OPENAI_API_KEY: {masked_key}")
    else:
        print(f"  ❌ OPENAI_API_KEY: 未设置")
    
    print(f"  📍 OPENAI_BASE_URL: {base_url}")
    print(f"  🤖 OPENAI_MODEL: {model}")
    print()
    
    if not api_key:
        print("⚠️  提示: 请设置 OPENAI_API_KEY 以运行 NL2SQL 示例")
        print("   export OPENAI_API_KEY='your-api-key'")
        print("   export OPENAI_BASE_URL='https://api.openai.com/v1'  # 可选")
        print("   export OPENAI_MODEL='gpt-4'  # 可选")
        print()


# ============================================================================
# 主函数
# ============================================================================

def main():
    """运行所有示例"""
    print("\n")
    print("🚀 DeepEye NL2SQL 示例")
    print("=" * 80)
    print()
    
    # 显示环境变量信息
    print_environment_info()
    
    # 创建测试数据库
    create_sample_database()
    
    # 运行示例
    example_4_schema_inspection()
    example_2_direct_query()
    example_1_nl2sql_basic()
    example_3_complete_pipeline()  # 需要 API Key，取消注释以运行
    
    print("=" * 80)
    print("✅ 所有示例运行完成！")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()


