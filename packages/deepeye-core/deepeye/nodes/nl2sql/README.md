# NL2SQL 模块

NL2SQL 模块提供了自然语言到 SQL 的转换能力，支持自动生成 SQL、执行查询和错误修复。

## 🎯 核心功能

### 1. 自然语言转 SQL
基于 LLM 将自然语言问题转换为 SQL 查询。

### 2. Schema-Aware
利用数据库 schema、示例数据和统计信息生成更准确的 SQL。

### 3. 自动执行
生成 SQL 后自动执行并返回 DataFrame 结果。

### 4. 错误自动修复
SQL 执行失败时自动分析错误并修复（最多重试 3 次）。

---

## 📦 NL2SQLNode

### 基本用法

```python
from deepeye.nodes.nl2sql import NL2SQLNode
from deepeye.nodes.io import NodeInput

# 创建节点
nl2sql = NL2SQLNode(
    node_id="nl2sql1",
    config={
        "api_key": "sk-...",
        "model": "gpt-4",
        "temperature": 0.0,
        "max_retries": 3,
        "verbose": True
    }
)

# 执行
outputs = nl2sql.run({
    "connection_string": NodeInput(data="sqlite:///sales.db"),
    "database_info": NodeInput(data={
        "schema": {...},
        "examples": {...},
        "statistics": {...},
        "dialect": "sqlite"
    }),
    "query": NodeInput(data="找出销售额前10的产品")
})

# 获取结果
sql = outputs["sql"].data
result_df = outputs["data"].data
explanation = outputs["explanation"].data
retries = outputs["data"].metadata.get("retries", 0)

print(f"生成的 SQL:\n{sql}")
print(f"\n查询结果:\n{result_df}")
print(f"\n解释: {explanation}")
print(f"\n重试次数: {retries}")
```

### 输入端口

| 端口名 | 类型 | 必需 | 说明 |
|--------|------|------|------|
| `connection_string` | string | ✅ | 数据库连接字符串 |
| `database_info` | object | ✅ | 数据库信息（来自 DatabaseDataSourceNode） |
| `query` | string | ✅ | 用户的自然语言问题 |

### 输出端口

| 端口名 | 类型 | 说明 |
|--------|------|------|
| `sql` | string | 生成的 SQL 查询语句 |
| `data` | DataFrame | SQL 查询结果 |
| `explanation` | string | SQL 的自然语言解释 |

### 配置选项

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `api_key` | str | 环境变量 | LLM API 密钥 |
| `base_url` | str | `https://api.openai.com/v1` | LLM API 基础 URL |
| `model` | str | `gpt-4` | LLM 模型名称 |
| `temperature` | float | 0.0 | LLM 温度（建议使用 0 以获得确定性输出） |
| `max_retries` | int | 3 | 最大重试次数 |
| `timeout` | int | 60 | 超时时间（秒） |
| `max_rows` | int | 100000 | 查询结果的最大行数 |
| `verbose` | bool | False | 是否输出详细日志 |

---

## 🔧 Prompt 工程

### Prompt 结构

NL2SQL 使用精心设计的 prompt 模板，包含：

1. **数据库方言**: 指定目标数据库类型（SQLite, MySQL, PostgreSQL）
2. **Schema 信息**: 表结构、列、主键、外键、索引
3. **示例数据**: 每个表的实际数据示例
4. **统计信息**: 行数、唯一值、null 值、数值范围
5. **用户问题**: 自然语言查询

### 输出格式

LLM 响应使用结构化的 XML 格式：

```xml
<think>
[分析和推理]
- 用户在问什么？
- 需要哪些表/列？
- 需要什么 JOIN？
- 需要什么聚合/过滤/排序？
</think>

<sql>
[SQL 查询语句]
</sql>

<explanation>
[SQL 的自然语言解释]
</explanation>
```

### 示例 Prompt

```
# Database Information

## Database Dialect
sqlite

## Schema Information
### Tables
- products
- orders

### Table: products
**Columns:**
- `id`: INTEGER NOT NULL AUTO_INCREMENT
- `name`: VARCHAR(100) NOT NULL
- `price`: REAL NOT NULL

**Primary Key:** id

## Sample Data (First 3 rows)
### Table: products
- `id`: 1, 2, 3
- `name`: 'Laptop', 'Mouse', 'Keyboard'
- `price`: 999.99, 29.99, 79.99

## Statistics
### Table: products
- **Row Count:** 100
- `price`: 100 unique values, range: [9.99, 1999.99]

# User Question
找出价格最高的 5 个产品
```

---

## 🔄 错误修复机制

### 工作流程

1. **首次生成**: 基于 schema 和用户问题生成 SQL
2. **执行尝试**: 尝试执行 SQL
3. **错误捕获**: 如果失败，捕获错误信息
4. **分析修复**: 将错误信息传递给 LLM，生成修复后的 SQL
5. **重试执行**: 执行修复后的 SQL
6. **循环**: 重复步骤 3-5，最多 `max_retries` 次

### 常见错误类型

#### 1. 列名错误
```python
# 错误 SQL
SELECT product_name FROM products  # 列名应该是 name 不是 product_name

# LLM 分析错误并修复
SELECT name FROM products
```

#### 2. 语法错误
```python
# 错误 SQL
SELECT * FROM products WHERE price > 100 ORDER price DESC  # 缺少 BY

# 修复后
SELECT * FROM products WHERE price > 100 ORDER BY price DESC
```

#### 3. 聚合错误
```python
# 错误 SQL
SELECT category, COUNT(*) FROM products  # 缺少 GROUP BY

# 修复后
SELECT category, COUNT(*) FROM products GROUP BY category
```

### 修复示例

```python
nl2sql = NL2SQLNode(
    node_id="nl2sql",
    config={
        "api_key": "sk-...",
        "max_retries": 3,
        "verbose": True  # 查看修复过程
    }
)

outputs = nl2sql.run({...})

# 输出日志:
# [NL2SQL] 生成 SQL (attempt 1)...
# [NL2SQL] 执行 SQL: SELECT product_name FROM products
# [NL2SQL] 执行失败 (attempt 1): no such column: product_name
# [NL2SQL] 修复 SQL (attempt 2)...
# [NL2SQL] 执行 SQL: SELECT name FROM products
# [NL2SQL] 执行成功，返回 10 行

print(f"重试次数: {outputs['data'].metadata['retries']}")  # 1
```

---

## 🎯 使用场景

### 场景 1: 简单查询
```python
query = "显示所有用户"
# 生成 SQL: SELECT * FROM users
```

### 场景 2: 条件过滤
```python
query = "找出年龄大于 30 岁的用户"
# 生成 SQL: SELECT * FROM users WHERE age > 30
```

### 场景 3: 聚合统计
```python
query = "计算每个城市的用户数量"
# 生成 SQL: SELECT city, COUNT(*) as user_count FROM users GROUP BY city
```

### 场景 4: 多表 JOIN
```python
query = "显示每个用户的订单总额"
# 生成 SQL:
# SELECT u.name, SUM(o.amount) as total
# FROM users u
# JOIN orders o ON u.id = o.user_id
# GROUP BY u.id, u.name
```

### 场景 5: 排序和限制
```python
query = "找出销售额最高的 10 个产品"
# 生成 SQL:
# SELECT p.name, SUM(o.amount) as total_sales
# FROM products p
# JOIN orders o ON p.id = o.product_id
# GROUP BY p.id, p.name
# ORDER BY total_sales DESC
# LIMIT 10
```

### 场景 6: 复杂分析
```python
query = "计算每个月的平均订单金额和订单数量"
# 生成 SQL:
# SELECT 
#     strftime('%Y-%m', order_date) as month,
#     AVG(amount) as avg_amount,
#     COUNT(*) as order_count
# FROM orders
# GROUP BY month
# ORDER BY month
```

---

## 🔗 与其他节点的集成

### 完整分析链路

```python
from deepeye.nodes.database import DatabaseDataSourceNode
from deepeye.nodes.nl2sql import NL2SQLNode
from deepeye.nodes.datacoder import DataCoderNode
from deepeye.nodes.dataplot import DataPlotNode

# 1. 数据库内省
db_source = DatabaseDataSourceNode(
    node_id="db",
    config={"connection_string": "sqlite:///sales.db"}
)
db_outputs = db_source.run({})

# 2. NL2SQL 查询
nl2sql = NL2SQLNode(node_id="nl2sql", config={...})
sql_outputs = nl2sql.run({
    "connection_string": db_outputs["connection_string"],
    "database_info": db_outputs["database_info"],
    "query": NodeInput(data="每月销售额趋势")
})

# 3. 数据处理
datacoder = DataCoderNode(node_id="coder", config={...})
coder_outputs = datacoder.run({
    "data": sql_outputs["data"],
    "task": NodeInput(data="添加环比增长率")
})

# 4. 可视化
dataplot = DataPlotNode(node_id="plot", config={...})
plot_outputs = dataplot.run({
    "data": coder_outputs["result"],
    "task": NodeInput(data="画折线图")
})
```

---

## 📊 支持的查询类型

### ✅ 已支持

- [x] 简单 SELECT 查询
- [x] WHERE 条件过滤
- [x] ORDER BY 排序
- [x] LIMIT/OFFSET 分页
- [x] JOIN (INNER, LEFT, RIGHT, FULL)
- [x] GROUP BY 聚合
- [x] HAVING 聚合过滤
- [x] 子查询
- [x] UNION/INTERSECT/EXCEPT
- [x] 窗口函数（部分数据库）
- [x] 日期/时间函数
- [x] 字符串函数
- [x] 数学函数

### ⚠️ 限制

- INSERT/UPDATE/DELETE 操作（出于安全考虑）
- CREATE/DROP/ALTER 操作（出于安全考虑）
- 存储过程和触发器
- 事务控制语句

---

## 🧪 测试

运行测试：
```bash
pytest tests/nodes/test_nl2sql.py -v
```

测试覆盖：
- ✅ Prompt 格式化
- ✅ LLM 响应解析
- ✅ 成功的 SQL 生成和执行
- ✅ SQL 错误和自动修复
- ✅ 超过最大重试次数
- ✅ 缺少 API Key 处理
- ✅ 缺少必要输入处理

---

## 🔒 安全考虑

### 1. 只读查询
NL2SQL 设计为只读查询工具，不应该生成 INSERT/UPDATE/DELETE 等修改数据的 SQL。

### 2. SQL 注入防护
虽然 SQL 是 LLM 生成的，但仍然建议：
- 使用参数化查询（如果支持）
- 限制数据库用户权限为只读
- 监控生成的 SQL

### 3. 行数限制
设置 `max_rows` 防止返回过大的结果集导致内存溢出。

### 4. 超时控制
设置 `timeout` 防止长时间查询阻塞。

---

## 📈 性能优化

### 1. 温度设置
```python
# 使用 temperature=0.0 获得确定性输出
config = {"temperature": 0.0}
```

### 2. 缓存策略
```python
# 相同问题可以缓存 SQL（待实现）
# cache = {"query": "...", "sql": "..."}
```

### 3. 示例数据大小
```python
# DatabaseDataSourceNode 使用较小的 sample_size
config = {"sample_size": 3}  # 减少 token 消耗
```

### 4. 统计信息选择
```python
# 如果不需要详细统计，可以关闭
config = {"include_statistics": False}
```

---

## 🐛 故障排查

### LLM 响应格式错误
```python
# 检查 LLM 响应是否包含 <sql></sql> 标签
try:
    outputs = nl2sql.run({...})
except ValueError as e:
    print(f"LLM 响应格式错误: {e}")
```

### SQL 执行失败
```python
# 启用 verbose 模式查看详细信息
config = {"verbose": True}
```

### 连接超时
```python
# 增加超时时间
config = {"timeout": 120}
```

### API Key 问题
```python
# 方式 1: 配置中提供
config = {"api_key": "sk-..."}

# 方式 2: 环境变量
import os
os.environ["OPENAI_API_KEY"] = "sk-..."
```

---

## 📝 最佳实践

### 1. 明确的问题描述
```python
# ✅ 好的问题
"找出 2024 年 1 月销售额最高的 10 个产品"

# ❌ 模糊的问题
"产品"
```

### 2. 使用具体的列名
```python
# ✅ 好的问题
"按产品类别统计平均价格"

# ❌ 模糊的问题
"统计一下"
```

### 3. 指定时间范围
```python
# ✅ 好的问题
"显示最近 30 天的订单"

# ❌ 模糊的问题
"显示最近的订单"
```

### 4. 利用 schema 信息
```python
# 确保 DatabaseDataSourceNode 提供了完整的 schema 信息
config = {
    "sample_size": 10,           # 足够的示例数据
    "include_statistics": True   # 包含统计信息
}
```

---

## 🚀 未来增强

- [ ] SQL 查询优化建议
- [ ] 查询结果缓存
- [ ] 自然语言解释查询计划
- [ ] 支持更多数据库方言特性
- [ ] 交互式 SQL 调试
- [ ] 查询性能分析
- [ ] 支持存储过程和函数
- [ ] 多轮对话式查询


