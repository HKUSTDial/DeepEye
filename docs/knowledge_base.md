# 知识库系统说明

本文档介绍知识库系统的核心功能实现、使用方式和扩展方向。

## 核心功能

1) 知识库管理
- 支持创建、查看、更新、删除知识库（Knowledge Base）。
- 每个知识库属于当前用户。

2) 文档上传与解析
- 支持上传本地文件到 MinIO 持久化存储。
- 上传后触发异步任务解析文件并分片（chunk）。
- 目前支持的解析类型：
  - .txt / .md / .csv / .json：直接文本读取
  - .pdf：使用 pypdf 读取
  - .docx / .doc：使用 python-docx 读取

3) 检索与上下文注入
- 聊天时支持 @知识库名称 自动选择知识库。
- 后端通过 kb_ids 进行检索，命中结果拼接到上下文中提供给 agent。

## 主要结构

### 数据表

- knowledge_bases：知识库元信息
- knowledge_base_files：上传文件元信息（状态、存储路径等）
- knowledge_base_chunks：解析后的文本分片

### 主要后端模块

- `app/services/knowledge_base_service.py`
  - 负责上传、解析、分片、搜索逻辑
- `app/services/minio_service.py`
  - MinIO 基础读写
- `app/tasks/kb_tasks.py`
  - 异步解析任务
- `app/api/v1/knowledge_bases.py`
  - REST API 接口
- `app/tasks/agent_tasks.py`
  - chat 时注入知识库上下文

### 主要前端模块

- `pages/KnowledgeBases.tsx`：知识库列表页
- `pages/KnowledgeBaseDetail.tsx`：知识库详情与文件管理
- `components/ChatBox.tsx`：@mention 交互 + kb_ids 传参
- `stores/knowledgeBases.ts`：知识库数据缓存

## 使用方式

### 1) 创建知识库

- 左侧菜单点击「Knowledge Base」
- 点击「Create」创建知识库

### 2) 上传文件

- 进入知识库详情页
- 点击「Upload File」上传文件
- 文件状态会由 pending → processing → ready / failed

### 3) 聊天使用知识库

- 在聊天框输入 `@知识库名称` 选择知识库
- 发送消息后，系统会从该知识库检索相关文本并注入到上下文

## 运行与依赖

### 依赖

- MinIO：用于文件持久化
- Celery + Redis：用于异步解析任务
- pypdf / python-docx：用于 PDF/DOCX 解析

### 任务工作流

1) 上传文件 → 写入 MinIO
2) 创建 kb_file 记录
3) Celery 异步解析 → 分片写入 kb_chunk

## 扩展方向

1) 向量检索
- 当前检索为 LIKE 简易匹配。
- 可升级为向量检索（pgvector / Qdrant / Milvus）。

2) 更多文件类型
- 增加 PPTX、HTML、图片 OCR 等解析方式。

3) 更细粒度权限
- 支持共享、团队知识库、多用户协作。

4) 内容版本与回滚
- 支持文件版本记录、重新解析历史版本。

5) UI 优化
- 上传进度、解析进度、失败重试等体验增强。
