# DeepEye Core 快速开始

## 🚀 初始化开发环境

### 1. 运行初始化脚本

```bash
cd packages/deepeye-core
./setup.sh
```

这个脚本会：
- ✅ 检查 Python 版本（需要 >= 3.10）
- ✅ 安装 uv（如果未安装）
- ✅ 创建虚拟环境
- ✅ 安装项目依赖
- ✅ 创建 .env 配置文件

> 💡 **关于 uv**: 我们使用 [uv](https://github.com/astral-sh/uv) 作为包管理器，它比 pip 快 10-100 倍！

### 2. 配置环境变量

编辑 `.env` 文件，填入你的 API Keys：

```bash
# .env
DEEPEYE_LLM_API_KEY=sk-...
```

### 3. 激活虚拟环境（可选）

```bash
source .venv/bin/activate
```

> 💡 **提示**: 使用 `uv run` 可以不激活环境直接运行命令！

## 📚 常用命令

```bash
# 查看所有可用命令
make help

# 运行测试
make test

# 运行测试并查看覆盖率
make test-cov

# 代码格式化
make format

# 代码检查
make lint

# 清理临时文件
make clean

# 启动 Jupyter Lab
make jupyter
```

## 🏗️ 项目结构

```
deepeye-core/
├── deepeye/                    # 主包
│   ├── nodes/                  # 节点系统
│   ├── workflow/               # 工作流引擎
│   ├── runtime/                # 执行运行时
│   ├── agent/                  # 智能编排器
│   ├── optimizer/              # 优化引擎
│   ├── llm/                    # LLM 集成
│   └── ...
├── tests/                      # 测试
└── examples/                   # 示例
```

## 🧪 测试

### 运行所有测试

```bash
make test
```

### 运行特定测试

```bash
poetry run pytest tests/nodes/test_base.py
poetry run pytest tests/workflow/
```

### 查看测试覆盖率

```bash
make test-cov
# 在浏览器中打开 htmlcov/index.html
```

## 📖 开发指南

### 代码风格

- 遵循 PEP 8
- 使用 Black 格式化（line-length=100）
- 使用类型提示
- 编写文档字符串

### 提交前检查

```bash
# 1. 格式化代码
make format

# 2. 运行代码检查
make lint

# 3. 运行测试
make test

# 4. 查看覆盖率
make test-cov
```

### 创建新模块

1. 在相应目录创建 Python 文件
2. 实现功能和文档
3. 在 `__init__.py` 中导出
4. 在 `tests/` 创建对应测试
5. 运行测试确保通过

---

准备好开始了吗？运行 `./setup.sh` 开始开发！ 🎉

