# 示例数据库初始化脚本

这些脚本用于创建和初始化示例数据库，用于测试数据库连接和知识管理功能。

## 数据库类型

- **PostgreSQL**: `init_example_postgres.py`
- **MySQL**: `init_example_mysql.py`

## 快速开始

### 1. 启动示例数据库容器

示例数据库容器使用了 `example` profile，默认不会启动。需要使用 `--profile example` 参数：

```bash
# 启动所有示例数据库（推荐）
docker-compose --profile example up -d

# 或者只启动特定的示例数据库
docker-compose --profile example up -d postgres-example
docker-compose --profile example up -d mysql-example

# 或者同时启动两个
docker-compose --profile example up -d postgres-example mysql-example
```

**注意**: 默认的 `docker compose up -d` 不会启动示例数据库容器，只有使用 `--profile example` 时才会启动。

### 2. 初始化示例数据库

```bash
# 初始化 PostgreSQL 示例数据库
python scripts/init_example_postgres.py
# 或
uv run python scripts/init_example_postgres.py

# 初始化 MySQL 示例数据库
python scripts/init_example_mysql.py
# 或
uv run python scripts/init_example_mysql.py
```

## 数据库连接信息

### PostgreSQL 示例数据库

- **类型**: `postgresql` 或 `postgres`
- **主机**: `localhost`
- **端口**: `5433` (默认，可通过 `POSTGRES_EXAMPLE_PORT` 环境变量修改)
- **数据库名**: `ecommerce_example`
- **用户名**: `example_user`
- **密码**: `example_pass`

### MySQL 示例数据库

- **类型**: `mysql`
- **主机**: `localhost`
- **端口**: `3307` (默认，可通过 `MYSQL_EXAMPLE_PORT` 环境变量修改)
- **数据库名**: `ecommerce_example`
- **用户名**: `example_user`
- **密码**: `example_pass`

## 数据库结构

示例数据库包含一个电商系统的数据结构：

### 表结构

1. **categories** - 产品分类
   - id, name, description, created_at

2. **products** - 产品目录
   - id, category_id, name, description, price, stock_quantity, sku, created_at, updated_at

3. **users** - 用户账户
   - id, username, email, full_name, phone, address, created_at

4. **orders** - 订单
   - id, user_id, order_number, total_amount, status, shipping_address, created_at, updated_at

5. **order_items** - 订单项
   - id, order_id, product_id, quantity, unit_price, subtotal, created_at

### 示例数据

每个数据库包含：
- 5 个分类
- 12 个产品
- 5 个用户
- 15 个订单
- 多个订单项

## 环境变量

可以通过环境变量自定义连接参数：

### PostgreSQL

- `POSTGRES_EXAMPLE_HOST` - 主机地址 (默认: localhost)
- `POSTGRES_EXAMPLE_PORT` - 端口 (默认: 5433)
- `POSTGRES_EXAMPLE_DB` - 数据库名 (默认: ecommerce_example)
- `POSTGRES_EXAMPLE_USER` - 用户名 (默认: example_user)
- `POSTGRES_EXAMPLE_PASSWORD` - 密码 (默认: example_pass)

### MySQL

- `MYSQL_EXAMPLE_HOST` - 主机地址 (默认: localhost)
- `MYSQL_EXAMPLE_PORT` - 端口 (默认: 3307)
- `MYSQL_EXAMPLE_DB` - 数据库名 (默认: ecommerce_example)
- `MYSQL_EXAMPLE_USER` - 用户名 (默认: example_user)
- `MYSQL_EXAMPLE_PASSWORD` - 密码 (默认: example_pass)

## 在 DeepEye 中配置连接

1. 打开 DeepEye 前端
2. 进入数据库连接管理页面
3. 添加新连接，使用上述连接信息
4. 测试连接
5. 同步数据库架构以查看表结构

## 注意事项

- 这些示例数据库仅用于开发和测试
- 数据存储在 Docker volumes 中，删除容器不会删除数据（除非使用 `-v` 参数）
- 要完全重置数据库，可以删除容器和 volume：
  ```bash
  docker-compose --profile example down -v
  docker-compose --profile example up -d
  python scripts/init_example_postgres.py
  python scripts/init_example_mysql.py
  ```

## 依赖

确保已安装以下 Python 包：

- `psycopg2` - PostgreSQL 连接
- `pymysql` - MySQL 连接

安装方式：

```bash
uv add psycopg2-binary pymysql
# 或
pip install psycopg2-binary pymysql
```

