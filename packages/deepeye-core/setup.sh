#!/bin/bash
# DeepEye Core 开发环境初始化脚本 (使用 uv)

set -e

echo "🚀 DeepEye Core 开发环境初始化"
echo "================================"
echo "使用工具: uv (超快的 Python 包管理器)"
echo ""

# 检查 uv
echo ""
echo "📌 检查 uv..."
if command -v uv &> /dev/null; then
    echo "✅ uv 已安装: $(uv --version)"
else
    echo "❌ uv 未安装"
    echo "📥 正在安装 uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "✅ uv 安装完成"
    echo ""
    echo "⚠️  请运行以下命令将 uv 添加到 PATH："
    echo "    source \$HOME/.cargo/env"
    echo ""
    echo "然后重新运行此脚本"
    exit 0
fi

# 创建虚拟环境
echo ""
echo "📌 创建虚拟环境..."
if [ ! -d ".venv" ]; then
    uv venv
    echo "✅ 虚拟环境已创建"
else
    echo "✅ 虚拟环境已存在"
fi

# 激活虚拟环境提示
echo ""
echo "📌 激活虚拟环境..."
echo "   运行: source .venv/bin/activate"

# 安装依赖
echo ""
echo "📌 安装项目依赖..."
uv add --default-index https://pypi.tuna.tsinghua.edu.cn/simple requests
uv pip install -e ".[dev,docs]"
echo "✅ 依赖安装完成"

# 创建 .env 文件
if [ ! -f .env ]; then
    echo ""
    echo "📌 创建 .env 配置文件..."
    cat > .env << 'EOF'
# DeepEye Core 配置

# LLM API Keys
DEEPEYE_LLM_API_KEY=your_openai_api_key_here
DEEPEYE_LLM_BASE_URL=your_openai_base_url_here
DEEPEYE_LLM_MODEL=your_openai_model_here

# 日志级别
LOG_LEVEL=INFO

# 开发模式
DEV_MODE=true
EOF
    echo "✅ .env 文件已创建，请编辑并填入你的 API Keys"
fi

# 创建 uv.lock（如果使用 uv sync）
echo ""
echo "📌 是否创建 uv.lock 文件？(y/n)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "生成 uv.lock..."
    uv lock
    echo "✅ uv.lock 已创建"
fi

echo ""
echo "================================"
echo "✨ 初始化完成！"
echo ""
echo "📚 uv 工具速查："
echo "  uv --version                # 查看版本"
echo "  uv pip install <package>    # 安装包"
echo "  uv run <command>            # 运行命令"
echo "  uv sync                     # 同步依赖（推荐）"
echo ""
echo "下一步："
echo "  1. 激活虚拟环境: source .venv/bin/activate"
echo "  2. 编辑 .env 文件，填入你的 API Keys"
echo "  3. 运行 'make help' 查看可用命令"
echo "  4. 运行 'make test' 运行测试"
echo ""
echo "💡 提示："
echo "  - uv 比 pip/poetry 快 10-100 倍"
echo "  - 使用 'uv run pytest' 直接运行命令（无需激活环境）"
echo "  - 使用 'make sync' 同步所有依赖"
echo ""
echo "查看开发指南："
echo "  cat QUICKSTART.md"
echo ""
