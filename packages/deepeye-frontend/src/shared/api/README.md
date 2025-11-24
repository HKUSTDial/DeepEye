# API 架构说明

## 📁 目录结构

```
src/shared/api/
├── README.md           # 本文档
├── index.ts            # 统一导出入口
├── client.ts           # HTTP 客户端基础类
├── auth.ts             # 认证相关 API
├── nodes.ts            # 节点相关 API
└── workflow.ts         # 工作流相关 API

src/shared/config/
└── api.config.ts       # API 配置中心
```

## 🎯 设计原则

### 1. 统一配置管理
所有 API 配置集中在 `api.config.ts` 中管理：
- 基础 URL
- 超时时间
- 日志开关

### 2. 统一请求处理
所有 HTTP 请求通过 `APIClient` 类处理：
- 自动添加认证 Token
- 统一错误处理
- 请求/响应日志
- 超时控制

### 3. 模块化 API
按功能模块划分 API：
- `authAPI` - 认证相关
- `nodesAPI` - 节点相关
- `workflowAPI` - 工作流相关

## 📖 使用方式

### 方式 1：使用统一的 API 对象（推荐）

```typescript
import { api } from '@/shared/api'

// 认证
await api.auth.login({ username, password })
await api.auth.getCurrentUser()

// 节点
const nodes = await api.nodes.list()
const nodeInfo = await api.nodes.getInfo('text_input')

// 工作流
await api.workflow.execute(nodes, edges)
```

### 方式 2：按需导入

```typescript
import { nodesAPI, workflowAPI } from '@/shared/api'

const nodes = await nodesAPI.list()
await workflowAPI.execute(nodes, edges)
```

### 方式 3：直接使用客户端

```typescript
import { apiClient } from '@/shared/api'

const data = await apiClient.get('/custom-endpoint')
await apiClient.post('/custom-endpoint', { data })
```

## ⚙️ 配置

### 环境变量配置

在 `web/.env` 文件中配置：

```env
# API 基础 URL
VITE_API_BASE_URL=http://localhost:8123/api/v1

# 请求超时时间（毫秒）
VITE_API_TIMEOUT=30000
```

### 运行时配置

```typescript
import { apiConfig } from '@/shared/api'

// 查看当前配置
console.log(apiConfig.getConfig())

// 动态修改配置
apiConfig.updateConfig({
  baseURL: 'http://new-api-server:8123/api/v1',
  timeout: 60000,
})
```

## 📝 日志

开发环境下自动启用详细日志：

```
⚙️ API 配置
📍 Base URL: http://localhost:8123/api/v1
⏱️  Timeout: 30000 ms
📝 Logging: 启用

📡 API Request: GET http://localhost:8123/api/v1/nodes
✅ API Response: 200 OK
📦 Response Data: { total: 10, nodes: [...] }
```

生产环境下日志自动关闭。

## 🔐 认证

### Token 管理

```typescript
import { apiClient } from '@/shared/api'

// 设置 Token（登录后自动调用）
apiClient.setToken('your-jwt-token')

// 获取当前 Token
const token = apiClient.getToken()

// 清除认证信息（登出）
apiClient.clearAuth()
```

Token 自动保存在 `localStorage` 中，页面刷新后自动恢复。

### 自动添加 Authorization Header

所有请求自动添加 `Authorization: Bearer <token>` 头。

## ❌ 错误处理

### 统一错误格式

```typescript
interface APIError {
  message: string    // 错误消息
  status: number     // HTTP 状态码
  detail?: string    // 详细错误信息
}
```

### 错误处理示例

```typescript
import { api, type APIError } from '@/shared/api'

try {
  await api.nodes.list()
} catch (error) {
  const apiError = error as APIError
  console.error(`错误 ${apiError.status}: ${apiError.message}`)
  if (apiError.detail) {
    console.error('详情:', apiError.detail)
  }
}
```

### 特殊错误处理

- **401 未授权**：自动清除 Token，提示重新登录
- **超时**：抛出 "请求超时" 错误

## 🔄 完整示例

```typescript
import { api } from '@/shared/api'

async function loadAndExecuteWorkflow() {
  try {
    // 1. 加载节点列表
    const nodeList = await api.nodes.list()
    console.log(`加载了 ${nodeList.total} 个节点`)

    // 2. 获取节点详情
    for (const node of nodeList.nodes) {
      const info = await api.nodes.getInfo(node.node_type)
      console.log(`节点: ${info.metadata.display_name}`)
    }

    // 3. 执行工作流
    const result = await api.workflow.execute(nodes, edges)
    console.log('执行结果:', result)

  } catch (error) {
    console.error('操作失败:', error)
  }
}
```

