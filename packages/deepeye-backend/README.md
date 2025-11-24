# DeepEye Backend

DeepEye 后端 API 服务，提供节点管理、Agent 编排和账户管理功能。

## 快速开始

### 1. 安装依赖

使用 uv 安装依赖：

```bash
# 安装 uv (如果还没有安装)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 创建虚拟环境并安装依赖
uv venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 安装依赖
uv pip install -e .

# 安装开发依赖
uv pip install -e ".[dev]"
```

### 2. 配置环境变量

```bash
# 复制环境变量示例文件
cp env.example .env

# 编辑 .env 文件，配置数据库、JWT 密钥等
vim .env
```

### 3. 启动数据库

**方法 1: 使用快速设置脚本（推荐）**

```bash
./scripts/setup_postgres.sh
```

**方法 2: 手动使用 Docker Compose**

```bash
docker-compose up -d postgres
```

**方法 3: 使用本地 PostgreSQL**

需要先安装并创建数据库，详见 [PostgreSQL 部署指南](./docs/POSTGRESQL_DEPLOYMENT.md)。

### 4. 初始化数据库表

使用初始化脚本创建数据库表：

```bash
# 使用 Python
python scripts/init_db.py

# 或使用 uv
uv run python scripts/init_db.py
```

这个脚本会根据 SQLAlchemy 模型自动创建所有表。

> 📖 详细的 PostgreSQL 部署指南请查看 [docs/POSTGRESQL_DEPLOYMENT.md](./docs/POSTGRESQL_DEPLOYMENT.md)

### 5. 启动应用

```bash
# 开发模式（热重载）
uvicorn app.main:app --reload --port 8001

# 或使用 uv
uv run uvicorn app.main:app --reload --port 8001
```

访问 http://localhost:8001/docs 查看 API 文档。

## 开发

### 运行测试

```bash
pytest
```

### 代码格式化

```bash
# 格式化代码
black .
isort .

# 检查代码
ruff check .
mypy .
```

## 文档

- [PostgreSQL 部署指南](./docs/POSTGRESQL_DEPLOYMENT.md) - 详细的数据库部署和配置说明
- [后端开发计划](./cursor_docs/backend-development-plan.md) - 后端功能开发计划
- [开发文档索引](./cursor_docs/README.md) - 其他开发文档

## 技术栈

- **Web 框架**: FastAPI 0.115+
- **数据库**: PostgreSQL 16+
- **ORM**: SQLAlchemy 2.0+
- **认证**: JWT (python-jose)
- **包管理**: uv

## 项目结构

```
app/
├── api/              # API 路由
│   └── v1/           # API v1 版本
├── core/             # 核心功能（配置、认证等）
├── db/               # 数据库配置
├── models/           # 数据模型
│   ├── database/     # SQLAlchemy 模型
│   └── schemas/      # Pydantic 模型
├── services/         # 业务逻辑层
├── utils/            # 工具函数
└── main.py           # 应用入口
```

