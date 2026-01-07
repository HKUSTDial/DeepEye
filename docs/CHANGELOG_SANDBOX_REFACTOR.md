# DeepEye Sandbox 重构变更日志

> 此次重构主要围绕 **Docker Sandbox 持久化**、**跨进程容器发现**、**前端文件管理** 三个核心功能展开。

---

## 📋 变更概览

| 类别 | 新增 | 修改 | 删除 |
|------|------|------|------|
| 后端 Sandbox | 8 个文件 | 5 个文件 | 2 个文件 |
| 后端 API | 2 个文件 | 3 个文件 | - |
| 后端 Schema | 1 个文件 | 2 个文件 | 1 个文件 |
| 前端组件 | 4 个文件 | 4 个文件 | - |
| 前端 API | 1 个文件 | 2 个文件 | - |
| 配置文件 | 1 个文件 | 2 个文件 | - |

---

## 🏗️ 架构变更

### 1. Docker Sandbox 持久化 (Named Volumes)

**问题**: 之前容器销毁后数据丢失，需要依赖 MinIO 备份/恢复

**解决方案**: 使用 Docker Named Volumes 实现数据持久化

```
之前:
Container 销毁 → 数据丢失 → 需要从 MinIO 恢复

现在:
Container 销毁 → Volume 保留 → 新容器自动挂载 → 数据即时可用
```

**涉及文件**:
- `packages/backend/app/sandbox/docker_sandbox.py` - 添加 volume 支持
- `packages/backend/app/sandbox/manager.py` - volume 生命周期管理

### 2. 跨进程容器发现 (Docker Labels)

**问题**: FastAPI 和 Celery Worker 在不同进程，无法共享内存中的容器引用

**解决方案**: 使用 Docker Labels 标记容器，通过 Docker API 查询

```python
# 创建容器时添加标签
labels = {
    "app": "deepeye",
    "component": "sandbox",
    "session_id": session_id,
    "volume": volume_name
}

# 跨进程查找
docker.containers.list(filters={"label": f"session_id={session_id}"})
```

**涉及文件**:
- `packages/backend/app/sandbox/manager.py` - `_find_containers_by_session()`
- `packages/backend/app/sandbox/docker_sandbox.py` - labels 添加

### 3. 前端文件管理系统

**新增功能**:
- 文件树展示 (FileExplorer + FileTreeItem)
- 文件预览 (FileViewer)
- 语法高亮 (useCodeHighlight + Shiki)
- 右键菜单 (下载/删除)
- 实时刷新 (SSE 事件驱动)

---

## 📁 新增文件

### 后端 Sandbox 模块
```
packages/backend/app/sandbox/
├── __init__.py          # 模块导出
├── docker_sandbox.py    # Docker 容器封装 (Named Volumes)
├── manager.py           # Sandbox 生命周期管理
├── factory.py           # 工厂模式创建
├── storage.py           # MinIO 备份/恢复
└── activity.py          # 活动时间追踪
```

### 后端 API
```
packages/backend/app/api/
├── sandbox.py           # Sandbox 状态 API
└── sandbox_files.py     # 文件操作 API (列表/读取/下载/删除)
```

### 前端组件
```
packages/frontend/src/components/
├── FileExplorer.vue     # 文件树容器
├── FileTreeItem.vue     # 树节点 (递归 + 右键菜单)
└── FileViewer.vue       # 文件预览 (代码/图片/CSV/Markdown)

packages/frontend/src/composables/
└── useCodeHighlight.ts  # Shiki 语法高亮
```

### 前端 API
```
packages/frontend/src/api/
└── sandbox.ts           # Sandbox 文件 API 客户端
```

---

## 🔧 修改文件

### 后端

| 文件 | 修改内容 |
|------|----------|
| `app/tasks/agent_tasks.py` | 使用 `get_or_create_sandbox()` 复用容器；发送 SSE 事件 |
| `app/schemas/events.py` | 新增 `SandboxEventType` 和 `SandboxEvent` |
| `app/core/config.py` | 新增 Sandbox 相关配置项 |
| `app/main.py` | 启动时启动 cleanup task |
| `docker-compose.yml` | 添加 Docker socket 挂载 |

### 前端

| 文件 | 修改内容 |
|------|----------|
| `src/App.vue` | 添加文件面板 + 拖拽调整宽度 + 事件监听 |
| `src/components/Sidebar.vue` | 新建会话逻辑优化 + 标题打字动画 |
| `src/components/StepItem.vue` | 详情面板滚动支持 |
| `src/stores/chat.ts` | 添加 `filesChangedTrigger`、`sandboxStartedTrigger` |
| `src/composables/useChat.ts` | SSE 事件处理 (`sandbox_files_changed`、`sandbox_started`) |

---

## ❌ 删除文件

| 文件 | 原因 |
|------|------|
| `packages/backend/app/schemas/internal.py` | 已合并到其他模块 |
| `packages/core/deepeye/tools/sandbox.py` | 重构到 `packages/backend/app/sandbox/` |

---

## 🔄 数据流变更

### Agent 执行流程 (新)

```
用户发送消息
    │
    ▼
FastAPI → Celery Task
    │
    ▼
get_or_create_sandbox(session_id)
    │
    ├── 本地缓存有? → 直接使用
    ├── Docker 有容器? → 重连 + 缓存
    └── 都没有? → 创建新容器 + Named Volume
            │
            ▼
        Volume 已存在? → 数据即时可用!
            │
            ▼
执行 bash 命令 → 发送 SSE 事件 (sandbox_files_changed)
            │
            ▼
前端收到事件 → 检查文件变化 → 有变化才刷新
```

### 文件刷新流程 (新)

```
后端执行命令成功
    │
    ▼
event_bus.publish("sandbox_files_changed")
    │
    ▼
前端 SSE 收到事件
    │
    ▼
chatStore.notifyFilesChanged()
    │
    ▼
FileExplorer watch 触发
    │
    ▼
获取新文件列表 → 比较 fingerprint
    │
    ├── 无变化 → 跳过刷新
    └── 有变化 → 更新 UI (保持展开状态)
```

---

## 🎨 UI 改进

### 1. 可拖拽侧边栏
- 文件面板宽度可拖拽调整 (25%-60%)
- 文件树/预览比例可调 (20%-50%)
- 拖拽时禁用 transition 动画

### 2. 会话标题动画
- 首次发送消息后，标题从 "New conversation" 变为用户输入
- 使用打字机动画效果

### 3. 文件预览优化
- txt 文件行号与内容同步滚动 (单一滚动容器)
- 行号固定在左侧 (`position: sticky`)
- hover 整行高亮

### 4. 右键菜单
- 文件/文件夹下载 (文件夹自动打包 ZIP)
- 删除 (带确认对话框)

---

## 📦 依赖变更

### 后端
```toml
# pyproject.toml
minio = "^7.2.0"  # MinIO 客户端 (备份存储)
```

### 前端
```json
// package.json
"lucide-vue-next": "^0.x.x",  // 图标库
"shiki": "^1.x.x"              // 语法高亮
```

---

## 🔑 关键配置

### docker-compose.yml
```yaml
backend-api:
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock  # Docker API 访问

backend-worker:
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
```

### 环境变量 (新增)
```bash
# Sandbox
SANDBOX_IMAGE=deepeye-sandbox:latest
SANDBOX_AUTO_BUILD=true
SANDBOX_AUTO_RESTORE=false
SANDBOX_IDLE_TIMEOUT=1800      # 30分钟
SANDBOX_ARCHIVE_TIMEOUT=86400  # 24小时
SANDBOX_CLEANUP_INTERVAL=300   # 5分钟

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SANDBOX_BUCKET=sandbox-backups
```

---

## ✅ 测试验证

1. **容器持久化**: 删除容器后重新创建，数据应保留
2. **跨进程发现**: Celery 创建的容器，FastAPI 能查到
3. **文件刷新**: 执行命令后文件列表自动更新
4. **下载功能**: 文件/文件夹下载正常

```bash
# 验证 volume
docker volume ls | grep deepeye-ws

# 验证容器 labels
docker inspect <container_id> | jq '.[0].Config.Labels'
```

---

## 📝 后续优化建议

1. **ActivityTracker 持久化**: 考虑使用 Redis 存储活动时间，解决多进程同步问题
2. **Volume 清理策略**: 定期清理长期未使用的 volumes
3. **文件操作权限**: 添加文件操作的权限控制
4. **大文件处理**: 添加文件大小限制和分页加载

