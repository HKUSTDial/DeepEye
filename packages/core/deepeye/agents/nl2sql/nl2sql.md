# NL2SQL 说明文档



## 1. 目标与范围

**目标**  
将自然语言问题转换为可执行 SQL，并接入 DeepEye 的 workflow 节点体系，支持数据库类数据源查询。

**范围**
- Core：NL2SQL Pipeline（值检索、schema linking、SQL 生成、修正、选择）
- Backend：新增 `nl2sql.generate` 节点接入 workflow
- 多数据库支持：SQLite + MySQL + Postgres（通过 SQLAlchemy extractor）

---

## 2. 分层架构

### 2.1 Backend（业务编排层）
- 负责工作流节点注册、执行器、会话、数据源管理
- DataSource 模型保存连接串/类型/文件元数据（与算法层元数据不同）
- 通过 workflow 节点调用 NL2SQL

关键文件：
- `packages/backend/app/node/nl2sql_generate.py`
- `packages/backend/app/node/data/sql_execute.py`
- `packages/backend/app/node/__init__.py`
- `packages/backend/app/models/datasource.py`

### 2.2 Core（算法能力层）
- `DatabaseMetadata` 抽象数据库结构（表/列/示例值/枚举/主外键）
- NL2SQL Pipeline 负责生成 SQL 并做修正与选择

关键文件：
- `packages/core/deepeye/agents/nl2sql/pipeline/nl2sql_pipeline.py`
- `packages/core/deepeye/datasource/datasource.py`
- `packages/core/deepeye/datasource/extractors/sqlite_extractor.py`
- `packages/core/deepeye/datasource/extractors/sqlalchemy_extractor.py`

---

## 3. NL2SQL Pipeline 组件说明

### 3.1 Value Retrieval（值检索）
- 从问题中提取关键词（LLM）
- 基于字符串相似度在列示例/枚举中找可能值
- 结果用于后续 schema linking

文件：
- `agents/nl2sql/value_retrieval/value_retrieval.py`

### 3.2 Schema Linking
- **Direct Linker**：LLM 直接选择相关表列
- **Value Linker**：基于检索值的距离筛选表列

文件：
- `agents/nl2sql/schema_linker/direct_linker.py`
- `agents/nl2sql/schema_linker/value_linker.py`
- `agents/nl2sql/schema_linker/reversed_linker.py`

### 3.3 SQL Generation
当前启用：
- DC（Divide & Conquer）
- Skeleton（Plan → Skeleton → Complete）


文件：
- `agents/nl2sql/sql_generation/dc_generation.py`
- `agents/nl2sql/sql_generation/skeleton_generation.py`
- `agents/nl2sql/sql_generation/icl_generation.py`

### 3.4 SQL Revision
一组规则 + LLM 修正的组合：
- Syntax / Join / MaxMin / OrderBy / Time / Select 等

文件：
- `agents/nl2sql/sql_revision/`


### 3.5 SQL Selection
对候选 SQL 执行、对比结果、投票选择最佳

文件：
- `agents/nl2sql/sql_selection/sql_selection.py`

---

## 4. Workflow 接入方式

新增节点：`nl2sql.generate`

**输入**
- `question`（必填）

**参数**
- `datasource_id` 或 `datasource_url`（至少一个）
- `datasource_type`（postgres | mysql | sqlite）
- `config`（NL2SQLPipelineConfig 的覆盖项）

**输出**
- `query`（SQL）

**典型工作流链路**
```
nl2sql.generate → sql.execute
```

---

## 5. 多数据库支持说明

### 5.1 SQLite
- 使用 `SQLiteExtractor`
- `database_path` 为本地文件路径

### 5.2 MySQL / Postgres
- 使用 `SQLAlchemyExtractor`
- `database_path` 使用连接串

**示例连接串**
- MySQL: `mysql+pymysql://user:pass@host:3306/dbname`
- Postgres: `postgresql+psycopg2://user:pass@host:5432/dbname`
- SQLite: `sqlite:////abs/path/to/file.db`

注意：MySQL/Postgres 需要安装对应驱动（如 `pymysql` / `psycopg2`）。

---

## 6. 性能与速度优化建议

默认 pipeline 会触发多轮 LLM 调用和 SQL 执行对比，可能较慢（3-5 分钟）。

**推荐快速配置**
```
NL2SQLPipelineConfig(
    value_retrieval_n_results=0,
    direct_linking_budget=1,
    dc_generation_budget=1,
    skeleton_generation_budget=0,
    revision_enabled=False,
    selection_top_k=1,
    selection_evaluator_budget=0,
)
```

运行时可配合：
```
pipeline.run(..., skip_value_retrieval=True, skip_revision=True, skip_selection=True)
```

---

## 7. 测试脚本

文件：`packages/core/tests/nl2sql_smoke.py`

### 7.1 SQLite 测试
```
export LLM_API_KEY=xxx
export LLM_BASE_URL=http://...
export LLM_MODEL=...
export NL2SQL_DB_PATH=/abs/path/to/db.sqlite
export NL2SQL_QUESTION="统计每个月的订单数量"
python packages/core/tests/nl2sql_smoke.py
```

### 7.2 MySQL/Postgres 测试
```
export LLM_API_KEY=xxx
export LLM_BASE_URL=http://...
export LLM_MODEL=...
export NL2SQL_DB_URL="mysql+pymysql://user:pass@host:3306/dbname"
export NL2SQL_QUESTION="统计每个月的订单数量"
python packages/core/tests/nl2sql_smoke.py
```

---

**Core**
- `packages/core/deepeye/agents/nl2sql/pipeline/nl2sql_pipeline.py`
- `packages/core/deepeye/agents/nl2sql/value_retrieval/value_retrieval.py`
- `packages/core/deepeye/agents/nl2sql/schema_linker/`
- `packages/core/deepeye/agents/nl2sql/sql_generation/`
- `packages/core/deepeye/agents/nl2sql/sql_revision/`
- `packages/core/deepeye/agents/nl2sql/sql_selection/sql_selection.py`

**Extractor**
- `packages/core/deepeye/datasource/extractors/sqlite_extractor.py`
- `packages/core/deepeye/datasource/extractors/sqlalchemy_extractor.py`

**Backend**
- `packages/backend/app/node/nl2sql_generate.py`
- `packages/backend/app/node/data/sql_execute.py`
