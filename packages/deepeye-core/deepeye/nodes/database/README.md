# Database 模块

Database 模块提供了统一的数据库访问和自然语言查询能力。

## 📦 模块组成

### 1. DatabaseConnection
底层数据库连接管理器，封装 SQLAlchemy 引擎。

**功能**:
- 支持多种数据库（SQLite, MySQL, PostgreSQL 等）
- 连接池管理
- Schema 内省（表、列、外键、索引）
- 示例数据采样
- 统计信息收集

**示例**:
```python
from deepeye.nodes.database import DatabaseConnection

# 创建连接
db = DatabaseConnection("sqlite:///sales.db")

# 获取表名
tables = db.get_table_names()

# 获取 schema 信息
schema = db.get_schema_info()

# 执行查询
df = db.execute_query("SELECT * FROM products LIMIT 10")
```

### 2. DatabaseDataSourceNode
统一的数据库数据源节点，支持两种工作模式。

#### 模式 1: 内省模式（不提供 sql 参数）
自动提取数据库 schema、示例数据、统计信息，用于驱动 NL2SQL。

**输出**:
- `connection_string`: 连接字符串（传递给下游节点）
- `database_info`: 数据库信息字典
  - `schema`: 表结构、列、主键、外键、索引
  - `examples`: 每个表的示例数据
  - `statistics`: 行数、唯一值、null 值统计
  - `dialect`: 数据库类型

**示例**:
```python
from deepeye.nodes.database import DatabaseDataSourceNode

# 内省模式
db_source = DatabaseDataSourceNode(
    node_id="db_introspect",
    config={
        "connection_string": "sqlite:///sales.db",
        "sample_size": 10,          # 每个表采样 10 行
        "include_statistics": True  # 包含统计信息
    }
)

outputs = db_source.run({})

# 获取输出
connection_string = outputs["connection_string"].data
database_info = outputs["database_info"].data

print(f"Tables: {database_info['schema']['tables']}")
print(f"Examples: {database_info['examples']}")
```

#### 模式 2: 查询模式（提供 sql 参数）
执行指定的 SQL 查询，返回 DataFrame 结果。

**输出**:
- `data`: 查询结果 DataFrame

**示例**:
```python
# 查询模式
db_query = DatabaseDataSourceNode(
    node_id="db_query",
    config={
        "connection_string": "sqlite:///sales.db",
        "sql": "SELECT * FROM products WHERE price > 100"
    }
)

outputs = db_query.run({})
df = outputs["data"].data
```

---

## 🔗 与 NL2SQL 的配合使用

### 基础流程

```python
from deepeye.nodes.database import DatabaseDataSourceNode
from deepeye.nodes.nl2sql import NL2SQLNode
from deepeye.nodes.io import NodeInput

# Step 1: 内省数据库
db_source = DatabaseDataSourceNode(
    node_id="db_introspect",
    config={
        "connection_string": "sqlite:///sales.db",
        "sample_size": 5
    }
)
introspect_outputs = db_source.run({})

# Step 2: NL2SQL 查询
nl2sql = NL2SQLNode(
    node_id="nl2sql",
    config={
        "api_key": "sk-...",
        "model": "gpt-4"
    }
)

nl2sql_outputs = nl2sql.run({
    "connection_string": introspect_outputs["connection_string"],
    "database_info": introspect_outputs["database_info"],
    "query": NodeInput(data="找出销售额前10的产品")
})

# 获取结果
sql = nl2sql_outputs["sql"].data
result_df = nl2sql_outputs["data"].data
explanation = nl2sql_outputs["explanation"].data

print(f"生成的 SQL: {sql}")
print(f"查询结果:\n{result_df}")
print(f"解释: {explanation}")
```

### 完整分析流程

```python
from deepeye.nodes.database import DatabaseDataSourceNode
from deepeye.nodes.nl2sql import NL2SQLNode
from deepeye.nodes.datacoder import DataCoderNode
from deepeye.nodes.dataplot import DataPlotNode

# 1. 内省数据库
db_source = DatabaseDataSourceNode(...)
introspect_outputs = db_source.run({})

# 2. NL2SQL 查询
nl2sql = NL2SQLNode(...)
nl2sql_outputs = nl2sql.run({...})

# 3. 数据处理
datacoder = DataCoderNode(...)
datacoder_outputs = datacoder.run({
    "data": nl2sql_outputs["data"],
    "task": NodeInput(data="添加环比增长率列")
})

# 4. 可视化
dataplot = DataPlotNode(...)
dataplot_outputs = dataplot.run({
    "data": datacoder_outputs["result"],
    "task": NodeInput(data="画折线图展示趋势")
})
```

---

## 🗄️ 支持的数据库

### SQLite
```python
"connection_string": "sqlite:///path/to/database.db"
"connection_string": "sqlite:////absolute/path/to/database.db"  # 绝对路径
```

### MySQL
```python
"connection_string": "mysql+pymysql://user:password@host:port/database"
```

**依赖**: `pip install pymysql`

### PostgreSQL
```python
"connection_string": "postgresql://user:password@host:port/database"
"connection_string": "postgresql+psycopg2://user:password@host:port/database"
```

**依赖**: `pip install psycopg2-binary`

---

## 📊 Schema 信息结构

```python
{
    "schema": {
        "tables": ["users", "orders", "products"],
        "columns": {
            "users": [
                {
                    "name": "id",
                    "type": "INTEGER",
                    "nullable": False,
                    "autoincrement": True
                },
                {
                    "name": "name",
                    "type": "VARCHAR(100)",
                    "nullable": False
                }
            ]
        },
        "primary_keys": {
            "users": ["id"]
        },
        "foreign_keys": {
            "orders": [
                {
                    "constrained_columns": ["user_id"],
                    "referred_table": "users",
                    "referred_columns": ["id"]
                }
            ]
        },
        "indexes": {
            "users": [
                {
                    "name": "idx_email",
                    "columns": ["email"],
                    "unique": True
                }
            ]
        }
    },
    "examples": {
        "users": {
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "email": ["alice@ex.com", "bob@ex.com", "charlie@ex.com"]
        }
    },
    "statistics": {
        "users": {
            "row_count": 1000,
            "columns": {
                "id": {
                    "type": "INTEGER",
                    "unique_count": 1000,
                    "null_count": 0,
                    "min": 1,
                    "max": 1000
                },
                "name": {
                    "type": "VARCHAR(100)",
                    "unique_count": 987,
                    "null_count": 0
                }
            }
        }
    },
    "dialect": "sqlite"
}
```

---

## ⚙️ 配置选项

### DatabaseDataSourceConfig

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `connection_string` | str | **必需** | 数据库连接字符串 |
| `sql` | str | None | SQL 查询（提供则进入查询模式） |
| `tables` | List[str] | None | 要内省的表（None = 所有表） |
| `sample_size` | int | 5 | 示例数据行数 |
| `include_statistics` | bool | True | 是否包含统计信息 |
| `max_rows` | int | 100000 | 查询结果的最大行数 |
| `timeout` | int | 60 | 查询超时时间（秒） |

---

## 🧪 测试

运行测试：
```bash
pytest tests/nodes/test_database.py -v
```

测试覆盖：
- ✅ 数据库连接创建和测试
- ✅ 表名获取
- ✅ Schema 内省
- ✅ SQL 查询执行
- ✅ 示例数据采样
- ✅ 统计信息收集
- ✅ 内省模式
- ✅ 查询模式
- ✅ 行数限制
- ✅ 错误处理

---

## 📝 示例

完整示例参见:
- `examples/nl2sql_example.py` - NL2SQL 完整流程示例

运行示例：
```bash
cd packages/deepeye-core
export OPENAI_API_KEY='your-api-key'
python examples/nl2sql_example.py
```

---

## 🔒 安全注意事项

1. **连接字符串**: 不要在代码中硬编码敏感信息（密码等），使用环境变量
2. **SQL 注入**: 使用参数化查询防止 SQL 注入
3. **行数限制**: 设置合理的 `max_rows` 避免内存溢出
4. **超时设置**: 设置 `timeout` 避免长时间查询阻塞

---

## 📈 性能优化

1. **连接池**: DatabaseConnection 使用连接池提高性能
2. **采样策略**: 使用 `sample_size` 限制示例数据量
3. **表过滤**: 使用 `tables` 参数只内省需要的表
4. **统计开关**: 如果不需要统计信息，设置 `include_statistics=False`

---

## 🐛 故障排查

### 连接失败
```python
# 检查连接字符串是否正确
db = DatabaseConnection("sqlite:///sales.db")
if not db.test_connection():
    print("Connection failed!")
```

### 驱动缺失
```bash
# MySQL
pip install pymysql

# PostgreSQL
pip install psycopg2-binary
```

### 查询超时
```python
# 增加超时时间
config = {
    "connection_string": "...",
    "timeout": 120  # 2 分钟
}
```

---

## 🚀 未来增强

- [ ] 支持更多数据库（Oracle, SQL Server, MongoDB）
- [ ] 查询缓存机制
- [ ] 分布式查询支持
- [ ] 查询性能分析
- [ ] 自动索引建议
- [ ] 数据质量检查


