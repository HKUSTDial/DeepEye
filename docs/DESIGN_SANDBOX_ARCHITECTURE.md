# DeepEye Sandbox 架构设计文档

> 本文档详细说明 Sandbox 模块的设计逻辑、代码结构和关键实现。

---

## 1. 问题背景

### 1.1 原始问题

```
用户发送消息 → Celery Worker 创建 Docker 容器 → 执行代码
                     ↓
            FastAPI 进程想访问这个容器
                     ↓
            ❌ 找不到！（不同进程，内存不共享）
```

### 1.2 数据丢失问题

```
容器运行中 → 用户离开 → 容器因空闲被销毁
                     ↓
            用户回来想继续
                     ↓
            ❌ 数据没了！
```

---

## 2. 解决方案设计

### 2.1 核心思路

```
┌─────────────────────────────────────────────────────────────────┐
│                      解决方案三要素                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Named Volumes     - 数据持久化，独立于容器生命周期           │
│                                                                  │
│  2. Docker Labels     - 容器元数据，支持跨进程查询               │
│                                                                  │
│  3. SSE Events        - 实时通知前端，文件变更自动刷新           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 后端代码设计

### 3.1 模块结构

```
packages/backend/app/sandbox/
│
├── docker_sandbox.py   # 底层：Docker 容器操作封装
│       │
│       ├── create()           # 创建容器 + Volume
│       ├── destroy()          # 销毁容器（保留 Volume）
│       ├── destroy_with_data()# 销毁容器 + Volume
│       └── exec_command()     # 执行命令
│
├── manager.py          # 中层：生命周期管理 + 跨进程发现
│       │
│       ├── get_or_create_sandbox()  # 优先复用
│       ├── get_sandbox()            # 查找（本地缓存 → Docker API）
│       ├── destroy_session()        # 销毁（可选删数据）
│       └── _reconnect_to_container()# 重连已存在容器
│
├── storage.py          # MinIO 备份/恢复（长期归档用）
├── activity.py         # 活动时间追踪
└── factory.py          # 工厂模式
```

### 3.2 DockerSandbox 设计

```python
class DockerSandbox:
    """
    核心属性:
    - container: Docker 容器对象
    - container_name: 容器名 (deepeye-sandbox-{timestamp})
    - volume_name: Volume 名 (deepeye-ws-{session_id})
    - session_id: 会话 ID
    """
    
    async def create(self, session_id: str = None):
        # 1. 确保镜像存在
        await self._ensure_image()
        
        # 2. 创建/复用 Named Volume
        self.volume_name = f"deepeye-ws-{session_id}"
        volume_existed = await self._ensure_volume()
        
        # 3. 创建容器，挂载 Volume
        self.container = docker.containers.run(
            image=SANDBOX_IMAGE,
            name=f"deepeye-sandbox-{timestamp}",
            labels={
                "app": "deepeye",
                "component": "sandbox",
                "session_id": session_id,      # 关键！用于跨进程查找
                "volume": self.volume_name     # 关键！记录 Volume 名
            },
            volumes={
                self.volume_name: {"bind": "/workspace", "mode": "rw"}
            }
        )
```

**设计要点**:
- `session_id` 作为 label，支持 `docker.containers.list(filters={"label": ...})`
- `volume_name` 也存入 label，重连时可恢复
- Volume 在 `create()` 时自动创建，在 `destroy()` 时保留

### 3.3 SandboxManager 设计

```python
class SandboxManager:
    """
    单例模式，管理所有 session 的 sandbox。
    
    核心数据结构:
    - _sandboxes: Dict[session_id, List[DockerSandbox]]  # 本地缓存
    - _docker: docker.from_env()                          # Docker 客户端
    """
    
    async def get_or_create_sandbox(self, session_id: str):
        """优先复用已存在的 sandbox"""
        
        # Step 1: 查本地缓存
        sandbox = await self.get_sandbox(session_id)
        if sandbox:
            return sandbox  # 复用！
        
        # Step 2: 没有则创建新的
        return await self.create_for_session(session_id)
    
    async def get_sandbox(self, session_id: str):
        """跨进程查找 sandbox"""
        
        # Step 1: 查本地缓存
        if session_id in self._sandboxes:
            return self._sandboxes[session_id][0]
        
        # Step 2: 查 Docker API (跨进程！)
        containers = self._find_containers_by_session(session_id)
        if containers:
            # 重连到已存在的容器
            sandbox = await self._reconnect_to_container(containers[0])
            self._sandboxes[session_id].append(sandbox)  # 加入缓存
            return sandbox
        
        return None
    
    def _find_containers_by_session(self, session_id: str):
        """通过 Docker labels 查找容器"""
        return self._docker.containers.list(
            all=True,  # 包括 stopped 的
            filters={
                "label": [
                    "app=deepeye",
                    "component=sandbox",
                    f"session_id={session_id}"
                ]
            }
        )
```

**设计要点**:
- 两级查找：本地缓存 → Docker API
- `_reconnect_to_container()` 从 container labels 恢复所有属性
- 单例模式确保全局只有一个 manager

### 3.4 跨进程发现流程

```
┌─────────────────┐                    ┌─────────────────┐
│  Celery Worker  │                    │    FastAPI      │
└────────┬────────┘                    └────────┬────────┘
         │                                      │
         │ create_for_session("abc")            │
         │         │                            │
         │         ▼                            │
         │ ┌───────────────┐                    │
         │ │   Container   │◄─── labels:        │
         │ │  + Volume     │     session_id=abc │
         │ └───────────────┘                    │
         │         │                            │
         │  存入 _sandboxes["abc"]              │
         │                                      │
         │                                      │ get_sandbox("abc")
         │                                      │         │
         │                                      │         ▼
         │                                      │  本地缓存? ❌
         │                                      │         │
         │                                      │         ▼
         │                     ┌────────────────┤  Docker API 查询
         │                     │                │  by labels
         │                     ▼                │         │
         │              找到容器!               │         ▼
         │                     │                │  _reconnect_to_container()
         │                     │                │         │
         │                     └────────────────┼─────────┘
         │                                      │
         │                                      ▼
         │                               sandbox 可用 ✅
```

---

## 4. 事件系统设计

### 4.1 事件定义

```python
# packages/backend/app/schemas/events.py

class SandboxEventType(str, Enum):
    STARTED = "sandbox_started"           # Sandbox 启动
    FILES_CHANGED = "sandbox_files_changed"  # 文件变更

class SandboxEvent(BaseModel):
    type: SandboxEventType
    source: str = "sandbox"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

### 4.2 事件发布

```python
# packages/backend/app/tasks/agent_tasks.py

async def _run_agent_async(...):
    # 获取/创建 sandbox
    sandbox = await sandbox_manager.get_or_create_sandbox(session_id)
    
    # 发送 "sandbox 启动" 事件
    await event_bus.publish(
        channel=f"session:{session_id}",
        data=SandboxEvent(type=SandboxEventType.STARTED).model_dump_json()
    )
    
    # 创建 bash 工具时，传入回调
    tools = get_sandbox_tools(
        sandbox,
        on_files_changed=lambda: asyncio.create_task(
            event_bus.publish(
                channel,
                SandboxEvent(type=SandboxEventType.FILES_CHANGED).model_dump_json()
            )
        )
    )
```

### 4.3 前端事件处理

```typescript
// packages/frontend/src/composables/useChat.ts

function connectToSSE(sessionId: string) {
    const eventSource = new EventSource(`/api/chat/${sessionId}/stream`)
    
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data)
        
        switch (data.type) {
            case 'sandbox_started':
                store.notifySandboxStarted()  // 触发打开文件面板
                break
            case 'sandbox_files_changed':
                store.notifyFilesChanged()    // 触发文件刷新
                break
            // ... 其他事件
        }
    }
}
```

---

## 5. 前端文件管理设计

### 5.1 组件结构

```
App.vue
├── Sidebar.vue           # 会话列表
├── ChatBox.vue           # 聊天区域
└── [Files Panel]
    ├── FileExplorer.vue  # 文件树容器
    │   └── FileTreeItem.vue  # 递归树节点
    └── FileViewer.vue    # 文件预览
```

### 5.2 智能刷新设计

```typescript
// packages/frontend/src/components/FileExplorer.vue

// 文件指纹：path + type + size
function getFilesFingerprint(files: FileNode[]): string {
    return files
        .sort((a, b) => a.path.localeCompare(b.path))
        .map(f => `${f.path}|${f.type}|${f.size ?? 0}`)
        .join(';')
}

// 比较是否有变化
function hasFilesChanged(oldFiles, newFiles): boolean {
    if (oldFiles.length !== newFiles.length) return true
    return getFilesFingerprint(oldFiles) !== getFilesFingerprint(newFiles)
}

// 收到事件后，只在有变化时刷新
watch(() => chatStore.filesChangedTrigger, async () => {
    const response = await sandboxApi.listFiles(sessionId, '/workspace')
    
    if (!hasFilesChanged(rootFiles.value, response.files)) {
        console.debug('No changes, skip refresh')
        return  // 不刷新！
    }
    
    // 有变化，刷新 UI
    updateFilesUI(response.files)
})
```

**设计要点**:
- 不是每次事件都刷新，而是比较 fingerprint
- 刷新时保留展开状态（expandedPaths）
- 避免不必要的 UI 闪烁

### 5.3 右键菜单设计

```vue
<!-- FileTreeItem.vue -->
<template>
    <div @contextmenu="handleContextMenu">
        <!-- 文件/文件夹内容 -->
    </div>
    
    <!-- 右键菜单 (Teleport 到 body) -->
    <Teleport to="body">
        <div v-if="showContextMenu" class="context-menu" :style="menuPosition">
            <div @click="handleDownload">Download</div>
            <div @click="handleDelete">Delete</div>
        </div>
    </Teleport>
</template>

<script setup>
// 事件向上冒泡
const emit = defineEmits<{
    download: [path: string, type: 'file' | 'directory']
    delete: [path: string, name: string]
}>()
</script>
```

### 5.4 文件预览设计

```typescript
// 根据文件类型选择渲染方式
const viewerType = computed(() => {
    const ext = fileExtension.value
    
    if (contentType === 'image') return 'image'     // <img> 标签
    if (ext === 'md') return 'markdown'              // vue-markdown-render
    if (ext === 'csv') return 'csv'                  // <table> 渲染
    if (CODE_EXTENSIONS.includes(ext)) return 'code' // Shiki 高亮
    
    return 'text'  // 纯文本 + 行号
})
```

---

## 6. 行号同步设计

### 6.1 问题

```html
<!-- 之前：两个独立的滚动区域 -->
<div class="flex overflow-auto">
    <div class="line-numbers">...</div>  <!-- 独立滚动 -->
    <pre class="content">...</pre>        <!-- 独立滚动 -->
</div>
<!-- 结果：行号和内容滚动不同步 -->
```

### 6.2 解决方案

```html
<!-- 现在：单一滚动容器 + table 布局 -->
<div class="overflow-auto">
    <table>
        <tr v-for="(line, idx) in lines">
            <td class="line-number sticky left-0">{{ idx + 1 }}</td>
            <td class="content">{{ line }}</td>
        </tr>
    </table>
</div>
```

```css
.line-number {
    position: sticky;
    left: 0;
    background: #1e1e1e;  /* 防止内容透过 */
}
```

**设计要点**:
- table 的每行天然对齐
- `sticky` 让行号固定在左侧
- 单一滚动容器，垂直滚动自然同步

---

## 7. 会话标题动画设计

```typescript
// Sidebar.vue

// 监听 sessions 变化
watch(() => store.sessions, (newSessions, oldSessions) => {
    for (const newSession of newSessions) {
        const oldSession = oldSessions.find(s => s.id === newSession.id)
        
        // 检测：从 "New conversation" 变为用户输入
        if (oldSession?.title === 'New conversation' && 
            newSession.title !== 'New conversation') {
            animateTitle(newSession.id, newSession.title)
        }
    }
})

// 打字机动画
function animateTitle(sessionId: string, fullTitle: string) {
    let index = 0
    const interval = setInterval(() => {
        if (index < fullTitle.length) {
            animatingTitles.set(sessionId, fullTitle.slice(0, index + 1))
            index++
        } else {
            clearInterval(interval)
            animatingTitles.delete(sessionId)
        }
    }, 30)  // 30ms 一个字符
}
```

---

## 8. 设计总结

| 设计原则 | 体现 |
|----------|------|
| **单一职责** | DockerSandbox 只管容器，Manager 管生命周期，Storage 管备份 |
| **开闭原则** | 新增 SandboxEvent 类型不影响现有代码 |
| **依赖倒置** | 使用工厂模式创建 sandbox，便于替换实现 |
| **最小惊讶** | 文件只在真正变化时刷新，避免不必要的 UI 跳动 |
| **渐进增强** | Volume 优先，MinIO 作为可选的长期归档方案 |

