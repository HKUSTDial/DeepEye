# API 目录结构文档

## 📁 目录结构

```
packages/backend/app/api/
├── __init__.py
│
├── auth/                    # 🔓 认证相关（公开，不需要鉴权）
│   ├── __init__.py
│   ├── login.py            # POST /api/auth/login
│   ├── register.py         # POST /api/auth/register
│   └── refresh.py          # POST /api/auth/refresh
│
├── public/                  # 🌐 公开接口（不需要鉴权）
│   ├── __init__.py
│   └── health.py           # GET /api/public/health
│
└── v1/                      # 🔒 业务接口 v1（都需要鉴权）
    ├── __init__.py
    ├── sessions.py         # 会话管理
    ├── chat.py             # 聊天
    ├── datasources.py      # 数据源
    └── sandbox/            # 沙箱相关
        ├── __init__.py
        ├── management.py   # 沙箱管理
        └── files.py        # 文件操作
```

## 🔐 鉴权规则

### 白名单（不需要鉴权）

由 `app/core/middleware.py` 中的 `PUBLIC_PATH_PREFIXES` 控制：

```python
PUBLIC_PATH_PREFIXES = [
    "/api/auth/",      # 所有认证接口
    "/api/public/",    # 所有公开接口
    "/docs",           # Swagger 文档
    "/redoc",          # ReDoc 文档
    "/openapi.json",   # OpenAPI schema
]
```

### 需要鉴权（默认）

所有不在白名单中的路径都需要鉴权，包括：
- `/api/v1/*` - 所有业务接口

## 🌐 完整 API 路由表

### 认证 API（公开）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 用户登录 |
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/refresh` | 刷新 token |

### 公开 API（公开）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/public/health` | 健康检查 |

### 会话管理 API（需鉴权）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/sessions` | 获取用户的所有会话 |
| POST | `/api/v1/sessions` | 创建新会话 |
| GET | `/api/v1/sessions/{session_id}` | 获取指定会话 |
| PATCH | `/api/v1/sessions/{session_id}` | 更新会话标题 |
| DELETE | `/api/v1/sessions/{session_id}` | 删除会话 |
| GET | `/api/v1/sessions/{session_id}/messages` | 获取会话消息 |

### 聊天 API（需鉴权）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat/start` | 开始聊天 |
| GET | `/api/v1/chat/stream/{session_id}` | SSE 流式响应 |

### 数据源 API（需鉴权）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/datasources` | 获取用户的所有数据源 |
| POST | `/api/v1/datasources` | 创建数据源 |
| GET | `/api/v1/datasources/{id}` | 获取指定数据源 |
| DELETE | `/api/v1/datasources/{id}` | 删除数据源 |

### 沙箱 API（需鉴权）

#### 沙箱管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/sandbox` | 创建沙箱 |
| POST | `/api/v1/sandbox/{session_id}/destroy` | 销毁沙箱 |
| GET | `/api/v1/sandbox/{session_id}/status` | 获取沙箱状态 |

#### 文件操作

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/sandbox/files/sessions/{session_id}` | 列出文件 |
| GET | `/api/v1/sandbox/files/sessions/{session_id}/read` | 读取文件 |
| POST | `/api/v1/sandbox/files/sessions/{session_id}/write` | 写入文件 |
| POST | `/api/v1/sandbox/files/sessions/{session_id}/mkdir` | 创建目录 |
| DELETE | `/api/v1/sandbox/files/sessions/{session_id}/delete` | 删除文件/目录 |
| GET | `/api/v1/sandbox/files/sessions/{session_id}/download` | 下载文件/文件夹 |

## 🔧 鉴权机制

### 全局中间件

在 `app/main.py` 中注册：

```python
# 全局鉴权中间件
app.middleware("http")(auth_middleware)
```

### 依赖注入

在需要 `user_id` 的接口中使用：

```python
from app.core.deps import CurrentUserId

@router.get("/example")
async def example(user_id: CurrentUserId):
    # user_id 自动注入
    pass
```

### 工作流程

1. 请求到达 → 中间件拦截
2. 检查路径是否在白名单 → 是 → 放行
3. 检查路径是否在白名单 → 否 → 验证 JWT token
4. Token 有效 → 注入 `user_id` 到 `request.state`
5. Token 无效 → 返回 401
6. 路由处理函数通过 `CurrentUserId` 获取 `user_id`

## 📝 添加新 API 的步骤

### 公开 API

1. 在 `app/api/public/` 下创建文件
2. 在 `app/api/public/__init__.py` 中注册路由
3. ✅ 完成！（自动在白名单中）

### 需要鉴权的 API

1. 在 `app/api/v1/` 下创建文件
2. 在路由函数中添加 `user_id: CurrentUserId` 参数
3. 在 Repository 层添加 `user_id` 过滤
4. 在 `app/api/v1/__init__.py` 中注册路由
5. ✅ 完成！（自动需要鉴权）

## 🎯 设计原则

1. **职责单一**：
   - `auth/` 只管认证
   - `public/` 只管公开接口
   - `v1/` 只管业务逻辑

2. **版本隔离**：
   - 使用 `v1/` 为将来的 API 版本升级预留空间
   - 可以添加 `v2/` 而不影响 `v1/`

3. **安全默认**：
   - 默认所有 API 都需要鉴权
   - 白名单机制明确哪些可以公开

4. **清晰易维护**：
   - 一眼就能看出哪些需要鉴权
   - 目录结构反映 URL 结构

## 🔄 迁移说明

### 旧 API 路径 → 新 API 路径

| 旧路径 | 新路径 | 说明 |
|--------|--------|------|
| `/api/sessions` | `/api/v1/sessions` | 版本化 |
| `/api/chat/*` | `/api/v1/chat/*` | 版本化 |
| `/api/datasources` | `/api/v1/datasources` | 版本化 |
| `/api/sandbox/*` | `/api/v1/sandbox/*` | 版本化 |
| `/api/sandbox/files/*` | `/api/v1/sandbox/files/*` | 版本化 |

### 前端需要更新

前端 API 调用需要更新路径，添加 `/v1` 前缀。建议在前端配置中统一管理：

```typescript
// frontend/src/api/config.ts
export const API_BASE = '/api/v1'

// 使用时
const response = await fetch(`${API_BASE}/sessions`)
```

## ✨ 优势

1. **清晰的职责划分**：一看目录就知道哪些需要鉴权
2. **易于维护**：新增 API 只需放到对应目录
3. **版本管理**：支持多版本 API 并存
4. **安全性高**：默认鉴权，白名单机制
5. **扩展性强**：添加新模块很容易

