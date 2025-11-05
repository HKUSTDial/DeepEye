.PHONY: help install dev test lint format clean build sync

help:  ## 显示帮助信息
	@echo "可用的命令："
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## 安装依赖
	uv pip install -e .

dev:  ## 安装开发依赖
	uv pip install -e ".[dev,docs]"

sync:  ## 同步依赖（推荐使用）
	uv sync --extra dev --extra docs

test:  ## 运行测试
	uv run pytest

test-cov:  ## 运行测试并生成覆盖率报告
	uv run pytest --cov=deepeye --cov-report=html --cov-report=term

lint:  ## 代码检查
	uv run ruff check deepeye/
	uv run mypy deepeye/

format:  ## 代码格式化
	uv run black deepeye/ tests/
	uv run isort deepeye/ tests/

format-check:  ## 检查代码格式
	uv run black --check deepeye/ tests/
	uv run isort --check deepeye/ tests/

clean:  ## 清理临时文件
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .venv/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build:  ## 构建包
	uv build

publish:  ## 发布到 PyPI
	uv publish

shell:  ## 启动虚拟环境
	@echo "Run: source .venv/bin/activate"

jupyter:  ## 启动 Jupyter Lab
	uv run jupyter lab

tree:  ## 显示目录树
	tree -I '__pycache__|*.pyc|.pytest_cache|.mypy_cache|htmlcov|*.egg-info|.venv' -L 3


