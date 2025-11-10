# PostgreSQL 部署指南

本指南将帮助你将 DeepEye 后端数据库部署为 PostgreSQL。

## 目录

1. [本地开发环境设置](#本地开发环境设置)
2. [生产环境部署](#生产环境部署)
3. [初始化数据库](#初始化数据库)
4. [连接字符串格式](#连接字符串格式)
5. [故障排查](#故障排查)

## 本地开发环境设置

### 方法 1: 使用 Docker Compose (推荐)

我们提供了一个 `docker-compose.yml` 文件来快速启动 PostgreSQL 数据库。

#### 快速启动（使用默认配置）

```bash
cd packages/deepeye-backend
./scripts/setup_postgres.sh
```

或手动启动：

```bash
cd packages/deepeye-backend
docker-compose up -d postgres
```

#### 配置 PostgreSQL 账户密码

**重要：** PostgreSQL 的账户密码配置在 `.env` 文件中，而不是在 `docker-compose.yml` 中硬编码。

1. **创建或编辑 `.env` 文件：**

   ```bash
   cp env.example .env
   vim .env
   ```

2. **设置 PostgreSQL 配置变量：**

   ```env
   # PostgreSQL Docker 容器配置
   POSTGRES_DB=deepeye          # 数据库名
   POSTGRES_USER=deepeye         # 用户名
   POSTGRES_PASSWORD=your-strong-password-here  # 密码（生产环境请使用强密码！）
   POSTGRES_PORT=5432            # 端口
   ```

3. **（可选）设置 `DATABASE_URL`：**

   ```env
   # 数据库连接 URL（应用使用，可选）
   # 如果未设置，应用会自动从 POSTGRES_* 变量构建
   # 如果需要自定义连接字符串（如使用云数据库、SSL 等），可以手动设置
   # DATABASE_URL=postgresql+asyncpg://deepeye:your-strong-password-here@localhost:5432/deepeye
   ```

   **提示：** 应用会自动从 `POSTGRES_*` 变量构建 `DATABASE_URL`，通常无需手动设置。只有在需要自定义连接字符串（如云数据库、SSL 连接等）时才需要手动设置 `DATABASE_URL`。

4. **启动容器（使用新的配置）：**

   ```bash
   # 如果容器已存在，需要先删除并重新创建
   docker-compose down -v
   docker-compose up -d postgres
   ```

   **注意：** `docker-compose down -v` 会删除所有数据！如果已有数据，请先备份。

#### 默认配置（如果未设置环境变量）

如果 `.env` 文件中没有设置 `POSTGRES_*` 变量，将使用以下默认值：
- 数据库名: `deepeye`
- 用户名: `deepeye`
- 密码: `deepeye`
- 端口: `5432`

**⚠️ 警告：** 默认密码仅用于开发环境，生产环境必须修改！

### 方法 2: 本地安装 PostgreSQL

#### Ubuntu/Debian

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### macOS (使用 Homebrew)

```bash
brew install postgresql@15
brew services start postgresql@15
```

#### 创建数据库和用户

```bash
# 切换到 postgres 用户
sudo -u postgres psql

# 在 PostgreSQL shell 中执行：
CREATE DATABASE deepeye;
CREATE USER deepeye WITH PASSWORD 'deepeye';
GRANT ALL PRIVILEGES ON DATABASE deepeye TO deepeye;
ALTER DATABASE deepeye OWNER TO deepeye;
\q
```

### 配置环境变量

创建 `.env` 文件（如果还没有）：

```bash
cp env.example .env
```

`.env` 文件中的数据库配置：

**PostgreSQL 配置**（用于 `docker-compose.yml` 和应用）：
   ```env
   POSTGRES_DB=deepeye
   POSTGRES_USER=deepeye
   POSTGRES_PASSWORD=your-password-here
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   ```

**数据库连接 URL**（应用使用，可选）：
   ```env
   # 如果未设置，应用会自动从上面的 POSTGRES_* 变量构建
   # 只有在需要自定义连接字符串（如云数据库、SSL 等）时才需要手动设置
   # DATABASE_URL=postgresql+asyncpg://deepeye:deepeye@localhost:5432/deepeye
   ```

**重要提示：**
- 应用会自动从 `POSTGRES_*` 变量构建 `DATABASE_URL`，通常无需手动设置
- 只有在需要自定义连接字符串（如云数据库、SSL 连接、连接池参数等）时才需要手动设置 `DATABASE_URL`
- 如果设置了 `DATABASE_URL`，它将优先使用，不会从 `POSTGRES_*` 变量构建

## 生产环境部署

### 使用云数据库服务

#### AWS RDS

1. 在 AWS 控制台创建 PostgreSQL RDS 实例
2. 配置安全组允许应用服务器访问
3. 获取连接端点（endpoint）
4. 设置环境变量：

```env
DATABASE_URL=postgresql+asyncpg://username:password@your-rds-endpoint:5432/deepeye
```

#### Google Cloud SQL

1. 在 GCP 控制台创建 Cloud SQL PostgreSQL 实例
2. 配置授权网络
3. 获取连接名称
4. 使用 Cloud SQL Proxy 或直接连接

#### Azure Database for PostgreSQL

1. 在 Azure Portal 创建 PostgreSQL 服务器
2. 配置防火墙规则
3. 获取连接字符串

#### 自托管 PostgreSQL

在生产服务器上安装 PostgreSQL：

```bash
# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib

# 配置 PostgreSQL
sudo nano /etc/postgresql/15/main/postgresql.conf
# 确保 listen_addresses = '*' 或 'localhost'

sudo nano /etc/postgresql/15/main/pg_hba.conf
# 添加允许连接的规则
```

创建生产数据库：

```bash
sudo -u postgres psql
CREATE DATABASE deepeye_prod;
CREATE USER deepeye_user WITH PASSWORD 'strong-password-here';
GRANT ALL PRIVILEGES ON DATABASE deepeye_prod TO deepeye_user;
ALTER DATABASE deepeye_prod OWNER TO deepeye_user;
\q
```

### 安全最佳实践

1. **使用强密码**：生产环境必须使用强密码
2. **限制网络访问**：只允许应用服务器访问数据库
3. **使用 SSL 连接**：生产环境启用 SSL

```env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db?ssl=require
```

4. **定期备份**：设置自动备份策略
5. **监控**：设置数据库监控和告警

## 初始化数据库

首次部署时，需要初始化数据库表：

```bash
cd packages/deepeye-backend

# 确保环境变量已设置
export DATABASE_URL=postgresql+asyncpg://deepeye:deepeye@localhost:5432/deepeye
export SECRET_KEY=your-secret-key-here

# 初始化数据库表
python scripts/init_db.py
# 或使用 uv
uv run python scripts/init_db.py
```

### 验证初始化

检查数据库表是否创建成功：

```bash
psql -U deepeye -d deepeye -c "\dt"
```

应该看到以下表：
- `users`
- `password_reset_tokens`
- `workflows`

## 连接字符串格式

### 异步连接（应用使用）

```env
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database
```

### 带 SSL 的连接

```env
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/db?ssl=require
```

### 连接池配置

可以在连接字符串中添加连接池参数：

```env
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/db?pool_size=10&max_overflow=20
```

## 故障排查

### 连接错误

**错误：`could not connect to server`**

- 检查 PostgreSQL 服务是否运行：`sudo systemctl status postgresql`
- 检查端口是否正确（默认 5432）
- 检查防火墙设置
- 检查 `pg_hba.conf` 配置

**错误：`password authentication failed`**

- 验证用户名和密码是否正确
- 检查用户是否存在：`\du` 在 psql 中
- 重置密码：`ALTER USER username WITH PASSWORD 'newpassword';`

**错误：`database does not exist`**

- 创建数据库：`CREATE DATABASE deepeye;`
- 检查数据库名是否正确

### 初始化错误

**错误：`表已存在`**

如果表已经存在，`init_db.py` 脚本会跳过已存在的表，不会报错。如果需要重新创建表：

```bash
# 删除现有表（警告：会丢失所有数据！）
psql -U deepeye -d deepeye -c "DROP TABLE IF EXISTS workflows, password_reset_tokens, users CASCADE;"

# 重新初始化
python scripts/init_db.py
```

**错误：`无法连接到数据库`**

- 检查 `DATABASE_URL` 是否正确
- 检查 PostgreSQL 服务是否运行
- 检查网络连接和防火墙设置

### 性能问题

1. **连接池配置**：调整连接池大小
2. **索引优化**：确保外键字段有索引
3. **查询优化**：使用 `EXPLAIN ANALYZE` 分析慢查询
4. **监控**：使用 `pg_stat_statements` 扩展监控查询性能

## 测试连接

使用 Python 测试数据库连接：

```python
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

async def test_connection():
    engine = create_async_engine("postgresql+asyncpg://deepeye:deepeye@localhost:5432/deepeye")
    async with engine.connect() as conn:
        result = await conn.execute("SELECT version()")
        print(result.fetchone())

asyncio.run(test_connection())
```

或使用 psql 命令行工具：

```bash
psql -U deepeye -d deepeye -c "SELECT version();"
```

## 下一步

数据库配置完成后，你可以：

1. 运行应用：`uv run uvicorn app.main:app --reload`
2. 运行测试：`uv run pytest`
3. 访问 API 文档：`http://localhost:8000/docs`

## 参考资源

- [PostgreSQL 官方文档](https://www.postgresql.org/docs/)
- [SQLAlchemy PostgreSQL 文档](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html)
- [asyncpg 文档](https://magicstack.github.io/asyncpg/)

