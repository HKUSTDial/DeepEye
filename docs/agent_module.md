# Agent 模块说明（详细版）

## 作用
Agent 模块负责“决策 + 执行 + 事件输出”。  
它把用户请求拆成可执行步骤，并通过事件总线将过程推送到前端。

## 代码结构与调用链

1) 入口任务  
路径：`packages/backend/app/tasks/agent_tasks.py`  
职责：  
- 创建模型与回调  
- 注入可用工具  
- 调用 Supervisor 执行  

2) Supervisor 决策层  
路径：`packages/core/deepeye/agents/supervisor.py`  
职责：  
- 依据提示词判断调用哪个工具  
- 不直接执行业务逻辑  

3) ReAct 框架  
路径：`packages/core/deepeye/agents/react_agent.py`  
职责：  
- 绑定模型与工具  
- 运行“模型→工具→模型”的循环  

4) 子 Agent  
- WorkflowAgent：`packages/core/deepeye/agents/workflow_agent.py`  
- CodeAgent / SQLAgent：`packages/core/deepeye/agents/code_agent.py` / `sql_agent.py`（当前主链路未用）  

5) 事件与消息聚合  
路径：`packages/backend/app/tasks/callbacks.py`  
职责：  
- `AgentCallback` 把 token/tool 事件写入 Redis  
- `MessageCollector` 组装步骤并持久化  

## 核心功能类说明

- `SupervisorAgent`  
  - 仅负责工具选择  
  - 规则在提示词里定义  

- `WorkflowAgent`  
  - 负责生成 workflow JSON  
  - 调用 `create_workflow / update_workflow / run_workflow_from_file`  

- `AgentCallback`  
  - 统一输出 `tool_start / tool_end / workflow_event`  
  - 前端通过 SSE 订阅并渲染  

## 扩展方式

### 1) 新增一个专用 Agent
以“日志分析 Agent”为例：

1. 新建 Agent 类
```python
# packages/core/deepeye/agents/log_agent.py
from deepeye.agents.react_agent import ReActAgent

LOG_AGENT_PROMPT = "You are a log analysis assistant."

class LogAgent(ReActAgent):
    def __init__(self, model, tools=None, **kwargs):
        super().__init__(model=model, tools=tools or [], system_prompt=LOG_AGENT_PROMPT, **kwargs)
```

2. 新建工具
```python
# packages/backend/app/tools/log_tools.py
from deepeye.tools.base import tool

def create_search_log_tool():
    @tool
    async def search_log(query: str) -> str:
        return "log results"
    return search_log
```

3. 注入到 Supervisor
```python
# packages/backend/app/tasks/agent_tasks.py
tools.append(create_log_agent_tool(model, session_id, callbacks=[cb_log]))
```

4. Supervisor 提示词加入决策规则  
在 `packages/core/deepeye/agents/supervisor.py` 中添加：
```
如果用户询问日志，调用 query_log_agent。
```

### 2) 新增一个工具
- 新建工具函数，放在 `packages/backend/app/tools/`  
- 在 `agent_tasks.py` 里注入工具到 Supervisor  
- 更新 Supervisor 提示词说明何时使用  
