# 多用户鉴权系统设计方案

## 🎯 设计目标

1. **最小侵入**：不破坏现有代码结构
2. **渐进式迁移**：可以逐步接入，不需要一次性改完
3. **优雅解耦**：鉴权逻辑与业务逻辑分离
4. **安全可靠**：JWT + Refresh Token 机制
5. **多租户隔离**：用户数据完全隔离

## 📐 技术选型

### 后端鉴权方案：JWT (JSON Web Token)

**为什么选择 JWT？**
- ✅ 无状态，易扩展
- ✅ 天然支持分布式（Celery worker 也能验证）
- ✅ 前后端分离友好
- ✅ 支持 SSE（Server-Sent Events）

**Token 结构**：
```json
{
  "user_id": "uuid",
  "username": "john@example.com",
  "exp": 1234567890,
  "iat": 1234567890
}
```

### 前端存储方案：HttpOnly Cookie + LocalStorage

- **Access Token (15分钟)**：存储在 Memory（React State/Zustand）
- **Refresh Token (7天)**：存储在 HttpOnly Cookie
- **User Info**：存储在 LocalStorage（可选）

## 🏗️ 架构设计

### 1. 数据库 Schema 变更

#### 新增 `users` 表

```python
# packages/backend/app/models/user.py
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
import uuid
from datetime import datetime, timezone

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
```

#### 修改现有表（添加 `user_id` 外键）

```python
# packages/backend/app/models/chat_session.py (修改)
class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)  # 新增
    title: Mapped[str | None] = mapped_column(String(255), default=None)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
```

```python
# packages/backend/app/models/datasource.py (修改)
class DataSource(Base):
    __tablename__ = "datasources"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)  # 新增
    # ... 其他字段保持不变
```

### 2. 鉴权中间件 - 依赖注入模式

**核心优势**：使用 FastAPI 的依赖注入，零侵入现有路由！

```python
# packages/backend/app/core/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
import uuid

# JWT 配置
SECRET_KEY = "your-secret-key-here"  # 应该从环境变量读取
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15

security = HTTPBearer()

def create_access_token(user_id: uuid.UUID, username: str) -> str:
    """创建 JWT access token"""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "user_id": str(user_id),
        "username": username,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> dict:
    """验证 JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> uuid.UUID:
    """
    依赖注入函数：获取当前用户 ID
    
    用法：
    @app.get("/api/sessions")
    async def get_sessions(user_id: uuid.UUID = Depends(get_current_user_id)):
        # user_id 自动注入，无需手动解析 token
        pass
    """
    token = credentials.credentials
    payload = verify_token(token)
    return uuid.UUID(payload["user_id"])

# 可选：获取完整用户信息
async def get_current_user(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> User:
    """获取当前用户完整信息"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user
```

### 3. API 路由改造 - 渐进式接入

**策略**：通过依赖注入添加 `user_id` 参数，无需修改业务逻辑！

#### 改造前（无鉴权）

```python
# packages/backend/app/api/sessions.py
@router.get("/")
async def list_sessions(db: Session = Depends(get_db)):
    sessions = session_repo.list_all(db)
    return sessions
```

#### 改造后（有鉴权）

```python
# packages/backend/app/api/sessions.py
from app.core.auth import get_current_user_id

@router.get("/")
async def list_sessions(
    user_id: uuid.UUID = Depends(get_current_user_id),  # 新增依赖注入
    db: Session = Depends(get_db)
):
    sessions = session_repo.list_by_user(db, user_id)  # 添加用户过滤
    return sessions
```

**优势**：
- ✅ 只需在路由函数签名中添加一个参数
- ✅ 业务逻辑层只需添加 `user_id` 过滤
- ✅ 不需要修改现有的 service/repository 结构

### 4. Repository 层改造

```python
# packages/backend/app/repositories/session_repo.py
class SessionRepository:
    def list_by_user(self, db: Session, user_id: uuid.UUID) -> list[ChatSession]:
        """按用户查询会话"""
        return db.query(ChatSession).filter(ChatSession.user_id == user_id).all()
    
    def get_by_id_and_user(self, db: Session, session_id: uuid.UUID, user_id: uuid.UUID) -> ChatSession | None:
        """获取用户的特定会话（防止越权）"""
        return db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id
        ).first()
    
    def create_for_user(self, db: Session, user_id: uuid.UUID, title: str = None) -> ChatSession:
        """为用户创建会话"""
        session = ChatSession(user_id=user_id, title=title or "New conversation")
        db.add(session)
        db.commit()
        db.refresh(session)
        return session
```

### 5. 前端改造 - 拦截器模式

#### Zustand Auth Store

```typescript
// packages/frontend-react/src/stores/auth.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthStore {
  accessToken: string | null
  user: { id: string; username: string; email: string } | null
  isAuthenticated: boolean
  
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  refreshToken: () => Promise<void>
  setAccessToken: (token: string) => void
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      accessToken: null,
      user: null,
      isAuthenticated: false,
      
      login: async (email, password) => {
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
          credentials: 'include'  // 重要：发送和接收 cookies
        })
        
        if (!res.ok) throw new Error('Login failed')
        
        const data = await res.json()
        set({
          accessToken: data.access_token,
          user: data.user,
          isAuthenticated: true
        })
      },
      
      logout: () => {
        set({ accessToken: null, user: null, isAuthenticated: false })
        // 清除 refresh token cookie
        fetch('/api/auth/logout', { method: 'POST', credentials: 'include' })
      },
      
      refreshToken: async () => {
        const res = await fetch('/api/auth/refresh', {
          method: 'POST',
          credentials: 'include'
        })
        
        if (!res.ok) {
          get().logout()
          throw new Error('Session expired')
        }
        
        const data = await res.json()
        set({ accessToken: data.access_token })
      },
      
      setAccessToken: (token) => set({ accessToken: token })
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ user: state.user })  // 只持久化用户信息
    }
  )
)
```

#### HTTP 拦截器

```typescript
// packages/frontend-react/src/api/client.ts (修改)
import { useAuthStore } from '../stores/auth'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const { accessToken, refreshToken, logout } = useAuthStore.getState()
  
  // 自动添加 Authorization header
  const headers = new Headers(options.headers)
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`)
  }
  
  let response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: 'include'  // 重要：发送 cookies
  })
  
  // Token 过期，自动刷新
  if (response.status === 401) {
    try {
      await refreshToken()
      
      // 重新获取新 token 并重试请求
      const newToken = useAuthStore.getState().accessToken
      headers.set('Authorization', `Bearer ${newToken}`)
      
      response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
        credentials: 'include'
      })
    } catch (error) {
      // Refresh 失败，跳转登录页
      logout()
      window.location.href = '/login'
      throw error
    }
  }
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  
  return response.json()
}

export const http = {
  get: <T>(path: string) => request<T>(path, { method: 'GET' }),
  post: <T>(path: string, body?: unknown) => 
    request<T>(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined
    }),
  // ... put, patch, delete
}
```

#### 路由守卫

```typescript
// packages/frontend-react/src/App.tsx (添加)
import { useAuthStore } from './stores/auth'
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

function ProtectedApp() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const navigate = useNavigate()
  
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login')
    }
  }, [isAuthenticated, navigate])
  
  if (!isAuthenticated) {
    return <div>Loading...</div>
  }
  
  return <App />  // 原有的 App 组件
}
```

### 6. SSE 鉴权处理

SSE 无法在 header 中传 token，需要通过 URL 参数：

```python
# packages/backend/app/api/chat.py
@router.get("/stream/{session_id}")
async def stream_events(
    session_id: uuid.UUID,
    token: str = Query(...),  # Token 通过 URL 参数传递
    db: Session = Depends(get_db)
):
    # 手动验证 token
    payload = verify_token(token)
    user_id = uuid.UUID(payload["user_id"])
    
    # 验证用户是否有权访问该 session
    session = session_repo.get_by_id_and_user(db, session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # SSE 逻辑
    return EventSourceResponse(event_generator(session_id))
```

```typescript
// packages/frontend-react/src/api/chat.ts
export const chatApi = {
  createEventSource: (sessionId: string) => {
    const token = useAuthStore.getState().accessToken
    return new EventSource(
      `${API_BASE}/api/chat/stream/${sessionId}?token=${token}`
    )
  }
}
```

## 📦 实施步骤（渐进式）

### Phase 1: 基础设施（1-2天）

1. ✅ 添加 `User` model
2. ✅ 添加 `user_id` 到现有表（添加迁移脚本）
3. ✅ 实现 `app/core/auth.py`（JWT 工具）
4. ✅ 实现 `app/api/auth.py`（登录/注册/刷新 API）
5. ✅ 前端添加 `auth store`
6. ✅ 前端添加 HTTP 拦截器

### Phase 2: 路由改造（2-3天）

**优先级**：从核心业务开始
1. ✅ `/api/sessions/*` - 会话管理
2. ✅ `/api/chat/*` - 聊天接口
3. ✅ `/api/datasources/*` - 数据源管理
4. ✅ `/api/sandbox/*` - 沙箱文件操作

### Phase 3: 前端 UI（1-2天）

1. ✅ 登录页 `/login`
2. ✅ 注册页 `/register`
3. ✅ 路由守卫
4. ✅ 用户信息显示（头像/菜单）
5. ✅ 退出登录

### Phase 4: 数据迁移（可选）

如果已有生产数据：
1. ✅ 创建默认管理员用户
2. ✅ 将现有数据关联到管理员用户
3. ✅ 提供数据导出/导入工具

## 🔒 安全最佳实践

1. **密码加密**：使用 `bcrypt` 或 `argon2`
2. **HTTPS Only**：生产环境强制 HTTPS
3. **CORS 配置**：严格限制允许的域名
4. **Token 过期**：Access Token 15分钟，Refresh Token 7天
5. **Rate Limiting**：登录接口限流（防暴力破解）
6. **SQL 注入防护**：使用 ORM 参数化查询
7. **CSRF 保护**：SameSite Cookie + CSRF Token

## 📊 性能优化

1. **Token 缓存**：Redis 缓存已验证的 token（5分钟）
2. **数据库索引**：`user_id` 字段添加索引
3. **查询优化**：Repository 层添加 `user_id` 过滤
4. **连接池**：FastAPI + SQLAlchemy 连接池配置

## 🎯 总结

### 核心优势

1. **依赖注入模式**：
   - ✅ 零侵入现有业务逻辑
   - ✅ 鉴权逻辑与业务逻辑完全解耦
   - ✅ 可以逐个路由渐进式接入

2. **前端拦截器**：
   - ✅ 自动添加 Authorization header
   - ✅ 自动刷新过期 token
   - ✅ 现有 API 调用代码无需修改

3. **多租户隔离**：
   - ✅ 数据库层面完全隔离（user_id 外键）
   - ✅ Repository 层自动过滤
   - ✅ 无法跨用户访问数据

### 与其他方案对比

| 方案 | 侵入性 | 扩展性 | 安全性 | 推荐度 |
|------|-------|-------|-------|--------|
| **JWT + 依赖注入** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ 强烈推荐 |
| Session + Cookie | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⚠️ 不适合分布式 |
| OAuth 2.0 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⚠️ 过于复杂 |
| API Key | ⭐ | ⭐⭐ | ⭐⭐ | ❌ 不适合用户系统 |

## 📚 下一步

准备好开始实施了吗？我可以帮你：

1. 📝 生成完整的代码文件
2. 🗄️ 编写数据库迁移脚本
3. 🧪 编写单元测试和集成测试
4. 📖 创建 API 文档

请告诉我从哪个部分开始！

