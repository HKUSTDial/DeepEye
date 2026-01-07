# Sandbox 系统说明（详细版）

## 作用
Sandbox 系统提供隔离的执行环境，用于运行 python/工具命令，保证安全与可复用。

## 架构设计

1) SandboxManager  
路径：`packages/backend/app/sandbox/manager.py`  
职责：  
- 复用 session 对应的容器  
- 追踪活跃度  
- 自动 stop / destroy  

2) DockerSandbox  
路径：`packages/backend/app/sandbox/docker_sandbox.py`  
职责：  
- 负责容器生命周期  
- 提供 `exec_command` 执行命令  
- 挂载 volume 保留数据  

3) Sandbox 工具  
路径：`packages/backend/app/sandbox/tools.py`  
职责：  
- 提供 `bash` 工具给 agent 调用  

4) ActivityTracker  
路径：`packages/backend/app/sandbox/activity.py`  
职责：  
- 记录使用时间  
- 提供 idle 判断  

5) Cleanup 启动点  
路径：`packages/backend/app/main.py`  
职责：  
- 启动时启动 cleanup task  
- 关闭时清理所有 sandbox  

## 运行流程

1) Agent 启动 → 调用 `get_or_create_sandbox`  
2) 执行任务 → 记录活跃时间  
3) Cleanup 定时检查：  
   - 超过 `SANDBOX_IDLE_TIMEOUT` → stop  
   - 超过 `SANDBOX_DESTROY_TIMEOUT` → destroy  

## 扩展方式

### 示例：新增沙箱实现

1) 实现 SandboxProtocol
```python
# packages/backend/app/sandbox/custom_sandbox.py
from deepeye.sandbox import SandboxProtocol

class CustomSandbox(SandboxProtocol):
    async def create(self, session_id: str): ...
    async def exec_command(self, command: str): ...
    async def stop(self): ...
    async def destroy(self): ...
```

2) 注册到 factory
```python
# packages/backend/app/sandbox/factory.py
if sandbox_type == "custom":
    return CustomSandbox()
```

