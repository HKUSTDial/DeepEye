#!/bin/bash

# DeepEye MinIO 初始化脚本
# 用于启动 MinIO 服务并创建必要的 bucket

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查 Docker 是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    print_success "Docker 已安装"
}

# 检查 docker-compose 是否安装
check_docker_compose() {
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "docker-compose 未安装，请先安装 docker-compose"
        exit 1
    fi
    print_success "docker-compose 已安装"
}

# 加载环境变量
load_env() {
    if [ -f .env ]; then
        print_info "加载 .env 文件..."
        export $(cat .env | grep -v '^#' | xargs)
        print_success "环境变量已加载"
    else
        print_warning ".env 文件不存在，使用默认配置"
        export MINIO_ENDPOINT=${MINIO_ENDPOINT:-localhost:9000}
        export MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY:-minioadmin}
        export MINIO_SECRET_KEY=${MINIO_SECRET_KEY:-minioadmin}
        export MINIO_BUCKET=${MINIO_BUCKET:-deepeye}
    fi
}

# 启动 MinIO 容器
start_minio() {
    print_info "启动 MinIO 容器..."
    
    if docker-compose ps | grep -q "deepeye-minio.*Up"; then
        print_warning "MinIO 容器已在运行"
    else
        docker-compose up -d minio
        print_success "MinIO 容器已启动"
    fi
}

# 等待 MinIO 就绪
wait_for_minio() {
    print_info "等待 MinIO 服务就绪..."
    
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:9000/minio/health/live > /dev/null 2>&1; then
            print_success "MinIO 服务已就绪"
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 1
    done
    
    echo ""
    print_error "MinIO 服务启动超时"
    return 1
}

# 创建 bucket
create_bucket() {
    print_info "创建 bucket: ${MINIO_BUCKET}..."

    # 检查虚拟环境
    local python_cmd="python3"
    if [ -f ".venv/bin/python" ]; then
        python_cmd=".venv/bin/python"
    elif [ -f ".venv/Scripts/python.exe" ]; then
        python_cmd=".venv/Scripts/python.exe"
    fi

    # 使用 Python 脚本创建 bucket
    $python_cmd - <<EOF
from minio import Minio
from minio.error import S3Error
import sys

try:
    client = Minio(
        "${MINIO_ENDPOINT}",
        access_key="${MINIO_ACCESS_KEY}",
        secret_key="${MINIO_SECRET_KEY}",
        secure=False
    )
    
    if client.bucket_exists("${MINIO_BUCKET}"):
        print("Bucket '${MINIO_BUCKET}' 已存在")
    else:
        client.make_bucket("${MINIO_BUCKET}")
        print("Bucket '${MINIO_BUCKET}' 创建成功")
    
    sys.exit(0)
except S3Error as e:
    print(f"创建 bucket 失败: {e}")
    sys.exit(1)
except Exception as e:
    print(f"错误: {e}")
    sys.exit(1)
EOF
    
    if [ $? -eq 0 ]; then
        print_success "Bucket 创建完成"
    else
        print_error "Bucket 创建失败"
        return 1
    fi
}

# 显示 MinIO 信息
show_info() {
    echo ""
    print_success "MinIO 初始化完成！"
    echo ""
    echo "📊 MinIO 信息："
    echo "  - API 端点:     http://localhost:9000"
    echo "  - 控制台:       http://localhost:9001"
    echo "  - Access Key:   ${MINIO_ACCESS_KEY}"
    echo "  - Secret Key:   ${MINIO_SECRET_KEY}"
    echo "  - Bucket:       ${MINIO_BUCKET}"
    echo ""
    echo "🔐 登录控制台："
    echo "  访问 http://localhost:9001"
    echo "  用户名: ${MINIO_ACCESS_KEY}"
    echo "  密码:   ${MINIO_SECRET_KEY}"
    echo ""
}

# 主函数
main() {
    echo ""
    print_info "开始初始化 MinIO..."
    echo ""
    
    check_docker
    check_docker_compose
    load_env
    start_minio
    
    if wait_for_minio; then
        create_bucket
        show_info
    else
        print_error "MinIO 初始化失败"
        exit 1
    fi
}

# 运行主函数
main

