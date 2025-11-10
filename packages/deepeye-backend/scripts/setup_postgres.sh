#!/bin/bash
# PostgreSQL 快速设置脚本

set -e

echo "🚀 DeepEye Backend - PostgreSQL 设置脚本"
echo "=========================================="
echo ""

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装。请先安装 Docker："
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

# 检查 docker-compose 是否可用
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "❌ docker-compose 未找到。请安装 docker-compose。"
    exit 1
fi

echo "📦 启动 PostgreSQL 容器..."

# 尝试启动容器，捕获错误
if ! $DOCKER_COMPOSE up -d postgres 2>&1; then
    echo ""
    echo "❌ PostgreSQL 容器启动失败"
    echo ""
    echo "🔍 可能的原因："
    echo "   1. 网络连接问题（无法从 Docker Hub 拉取镜像）"
    echo "   2. Docker Hub 访问受限（可能需要配置镜像加速器）"
    echo ""
    exit 1
fi

echo ""
echo "⏳ 等待 PostgreSQL 启动..."
sleep 5

# 检查容器是否健康
if docker ps | grep -q deepeye-postgres; then
    echo "✅ PostgreSQL 容器已启动"
else
    echo "❌ PostgreSQL 容器启动失败"
    echo "   检查容器状态: docker ps -a | grep deepeye-postgres"
    echo "   查看日志: docker logs deepeye-postgres"
    exit 1
fi

echo ""
echo "📝 检查 .env 文件..."

if [ ! -f .env ]; then
    echo "📋 创建 .env 文件..."
    cp env.example .env
    echo "✅ .env 文件已创建"
    echo ""
    echo "⚠️  请编辑 .env 文件，设置以下配置："
    echo "   1. PostgreSQL 账户密码（POSTGRES_USER, POSTGRES_PASSWORD）"
    echo "   2. SECRET_KEY（可以使用 openssl rand -hex 32 生成）"
    echo ""
    echo "   编辑命令: vim .env"
else
    echo "✅ .env 文件已存在"
fi

echo ""
echo "🔍 检查环境变量配置..."

# 加载 .env 文件（如果存在）
if [ -f .env ]; then
    # 使用 source 或 export 来加载环境变量
    set -a
    source .env 2>/dev/null || true
    set +a
fi

# 读取 PostgreSQL 配置（带默认值）
POSTGRES_DB=${POSTGRES_DB:-deepeye}
POSTGRES_USER=${POSTGRES_USER:-deepeye}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-deepeye}
POSTGRES_HOST=${POSTGRES_HOST:-localhost}
POSTGRES_PORT=${POSTGRES_PORT:-5432}

# 生成预期的 DATABASE_URL（用于显示）
EXPECTED_DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"

# 检查 DATABASE_URL（可选，应用会自动从 POSTGRES_* 构建）
if [ -f .env ]; then
    CURRENT_DATABASE_URL=$(grep "^DATABASE_URL=" .env 2>/dev/null | cut -d'=' -f2- || echo "")
    
    if [ -z "$CURRENT_DATABASE_URL" ]; then
        echo "💡 DATABASE_URL 未设置，应用将自动从 POSTGRES_* 变量构建"
    elif [ "$CURRENT_DATABASE_URL" != "$EXPECTED_DATABASE_URL" ]; then
        echo "💡 DATABASE_URL 已设置，将优先使用（应用不会自动构建）"
    else
        echo "✅ DATABASE_URL 配置正确"
    fi
fi

echo ""
echo "📊 PostgreSQL 配置信息："
echo "   数据库名: ${POSTGRES_DB}"
echo "   用户名: ${POSTGRES_USER}"
echo "   密码: ${POSTGRES_PASSWORD}"
echo "   主机: ${POSTGRES_HOST}"
echo "   端口: ${POSTGRES_PORT}"
echo "   连接 URL: ${EXPECTED_DATABASE_URL}"
echo ""
echo "💡 提示："
echo "   - 这些配置在 .env 文件中设置（POSTGRES_* 变量）"
echo "   - 应用会自动从 POSTGRES_* 变量构建 DATABASE_URL，通常无需手动设置"
echo "   - 只有在需要自定义连接字符串（如云数据库、SSL 等）时才需要手动设置 DATABASE_URL"
echo "   - 修改 POSTGRES_* 配置后需要重新创建容器："
echo "     docker-compose down -v"
echo "     docker-compose up -d postgres"
echo "   - 生产环境请使用强密码！"

if grep -q "SECRET_KEY=" .env 2>/dev/null && ! grep -q "SECRET_KEY=your-secret-key-change-this" .env 2>/dev/null; then
    echo "✅ SECRET_KEY 已配置"
else
    echo "⚠️  请设置 SECRET_KEY（可以使用 openssl rand -hex 32 生成）"
fi
echo ""
echo "💡 下一步："
echo "   1. 确保 .env 文件配置正确"
echo ""
echo "   2. 初始化数据库表:"
echo "      python scripts/init_db.py"
echo "      或: uv run python scripts/init_db.py"
echo ""
echo "   3. 启动应用:"
echo "      uv run uvicorn app.main:app --reload"
echo ""
echo "📖 详细文档: docs/POSTGRESQL_DEPLOYMENT.md"
echo ""
echo "✨ 设置完成！"

