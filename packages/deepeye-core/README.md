# DeepEye Core 🔮

<div align="center">

**下一代 AI 驱动的数据分析与可视化编排引擎**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[English](README.md) | [中文文档](README_CN.md)

</div>

---

## 🎯 项目愿景

**DeepEye** 致力于构建一个**智能化、可编排、可扩展**的数据分析平台，让任何人都能通过自然语言与数据对话，自动生成洞察报告和可视化内容。

我们相信：
- 🧠 **AI 应该理解业务意图**，而不仅仅是执行命令
- 🔧 **数据流应该像乐高积木一样可组装**，而不是硬编码的脚本
- 🚀 **分析过程应该自动优化**，并行执行、智能缓存
- 🌐 **平台应该对开发者友好**，易于扩展和贡献

---

## 🌟 核心特性

### 1️⃣ **灵活的节点系统**
- 📦 **开箱即用的节点库**: NL2SQL、NL2Code、可视化、RAG、视频生成等
- 🔌 **插件式架构**: 5 分钟开发自定义节点
- 🎨 **类型安全的 I/O 接口**: 自动验证数据流

### 2️⃣ **智能工作流引擎**
- 🔄 **声明式构建**: 用 Python 或 YAML 定义复杂分析流程
- ✅ **自动验证**: 循环依赖检测、类型检查
- 💾 **序列化/反序列化**: 工作流即代码，版本控制友好

### 3️⃣ **AI 驱动的自动编排**
- 🤖 **多策略支持**: ReAct、Planner-Executor、ReWOO、TODO-Driven
- 🧩 **智能任务分解**: 将复杂业务问题拆解为可执行的工作流
- 🎯 **上下文感知**: 根据数据特征和用户历史自动选择最佳策略

### 4️⃣ **高性能执行运行时**
- ⚡ **并行执行优化**: 自动识别可并行节点，加速分析
- 💾 **智能缓存**: 中间结果缓存，避免重复计算
- 🔀 **模型路由**: 根据任务复杂度选择最合适的 LLM

### 5️⃣ **全面的可观测性**
- 📊 **实时监控**: 跟踪每个节点的执行状态和性能
- 🔍 **链路追踪**: 端到端追踪数据流转过程
- 📈 **指标收集**: 成本、延迟、准确率等关键指标

---

## 🚀 快速开始

### 安装

```bash
# 使用 pip 安装（即将支持）
pip install deepeye-core
```

---

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                     用户接口层                                 │
│        (自然语言、Python API、低代码编辑器)                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   🤖 AI 编排层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 任务规划器    │  │ 策略选择器    │  │ 工作流生成器  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   🔄 工作流引擎                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 图构建器      │  │ 验证器        │  │ 序列化器      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   ⚡ 执行运行时                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 调度器        │  │ 执行器        │  │ 上下文管理    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   🧩 节点生态系统                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ NL2SQL  │ │ NL2Code │ │ 可视化   │ │  RAG    │  ...      │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   🛠️ 基础设施层                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ LLM 集成 │ │ 存储抽象 │ │ 可观测性 │ │ 优化引擎  │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎨 使用场景

### 📊 **企业数据分析**
- 自动生成周报、月报
- 异常检测和根因分析
- 多维度数据钻取

### 🔍 **智能问答系统**
- 基于企业数据库的自然语言查询
- 结合 RAG 的知识增强问答
- 多轮对话式数据探索

### 📈 **自动化报告生成**
- 从原始数据到可视化报告一键生成
- 支持 PDF、PPT、视频等多种输出格式
- 可定制的报告模板

### 🎬 **数据故事视频**
- 将数据分析结果转化为视频内容
- 自动配音和字幕生成
- 适合社交媒体传播

---

## 🤝 如何贡献

我们非常欢迎各种形式的贡献！无论你是：

- 🐛 **发现 Bug** → [提交 Issue](https://github.com/your-org/DeepEye/issues/new?template=bug_report.md)
- 💡 **有新想法** → [功能建议](https://github.com/your-org/DeepEye/issues/new?template=feature_request.md)
- 🔧 **想写代码** → 查看 [待认领任务](https://github.com/your-org/DeepEye/labels/good%20first%20issue)
- 📖 **完善文档** → [文档贡献指南](CONTRIBUTING.md#documentation)
- 🧩 **开发节点** → [自定义节点教程](docs/custom_nodes.md)

### 贡献者快速指南

1. **Fork 本仓库**
2. **克隆到本地**: `git clone https://github.com/YOUR_USERNAME/DeepEye.git`
3. **创建分支**: `git checkout -b feature/amazing-feature`
4. **安装依赖**: `poetry install`
5. **运行测试**: `poetry run pytest`
6. **提交代码**: `git commit -m 'Add amazing feature'`
7. **推送分支**: `git push origin feature/amazing-feature`
8. **发起 Pull Request**

查看完整的 [贡献指南](CONTRIBUTING.md)。

---

## 📚 文档

- [📖 完整文档](https://deepeye.readthedocs.io/)
- [🚀 快速入门教程](docs/quickstart.md)
- [🏗️ 架构设计](docs/architecture.md)
- [🧩 自定义节点开发](docs/custom_nodes.md)
- [🤖 Agent 编排策略](docs/orchestration.md)
- [⚡ 性能优化指南](docs/performance.md)
- [📊 最佳实践](docs/best_practices.md)

---

## 🌍 社区

加入我们的社区，与其他开发者交流：

- 💬 **Discord**: [加入讨论](https://discord.gg/deepeye)
- 🐦 **Twitter**: [@DeepEyeAI](https://twitter.com/DeepEyeAI)
- 📧 **邮件列表**: [订阅更新](mailto:dev@deepeye.ai)
- 📝 **技术博客**: [blog.deepeye.ai](https://blog.deepeye.ai)

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源。

---

## 🙏 致谢

DeepEye 站在巨人的肩膀上，感谢以下优秀的开源项目：

- [NetworkX](https://github.com/networkx/networkx) - 图结构处理
- [Pydantic](https://github.com/pydantic/pydantic) - 数据验证
- [FastAPI](https://github.com/tiangolo/fastapi) - API 框架
- [Plotly](https://github.com/plotly/plotly.py) - 可视化库

---

## ⭐ Star History

如果 DeepEye 对你有帮助，请给我们一个 Star ⭐！

[![Star History Chart](https://api.star-history.com/svg?repos=your-org/DeepEye&type=Date)](https://star-history.com/#your-org/DeepEye&Date)

---

<div align="center">

**用 AI 的眼睛，洞察数据的真相 👁️**

Made with ❤️ by the DeepEye Community

</div>
