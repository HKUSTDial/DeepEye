# 节点系统架构说明

## 概述

DeepEye 前端节点系统采用**后端驱动的动态加载架构**，所有节点定义、执行逻辑都由后端提供。

## 核心设计原则

### 1. 后端驱动
- **节点定义**：所有节点在后端使用 `@register_node` 装饰器注册
- **节点执行**：所有节点逻辑在后端执行
- **元数据提供**：后端提供节点的完整元数据（端口、属性、分类等）

### 2. 前端职责
- **动态加载**：从后端API加载节点列表和详细信息
- **UI渲染**：根据后端元数据自动生成节点UI
- **工作流编排**：提供可视化画布进行节点连接
- **执行调度**：调用后端API执行工作流

## 目录结构

```
nodes/
├── loader/                 # 节点加载器
│   ├── backendNodeLoader.ts    # 从后端加载节点
│   ├── BackendNodeExecutor.ts  # 后端节点执行器（已废弃）
│   └── index.ts
├── registry/              # 节点注册表
│   ├── NodeRegistry.ts         # 单例注册表
│   └── index.ts
├── types/                 # 类型定义
│   └── index.ts
├── components/            # 节点UI组件
│   ├── UnifiedNode.tsx         # 统一节点组件
│   ├── AIAssistedNode.tsx      # AI辅助节点组件
│   └── shared/                 # 共享组件
├── decorators/            # 装饰器（保留以备将来使用）
│   ├── Node.ts
│   ├── Input.ts
│   ├── Output.ts
│   ├── Property.ts
│   ├── View.ts
│   └── AIAssisted.ts
├── polyfills/             # Polyfills
│   └── reflect-metadata.ts
└── index.ts               # 入口文件
```

## 工作流程

### 1. 应用启动
```typescript
// main.tsx
function AppBootstrap() {
  useEffect(() => {
    async function initializeNodes() {
      // 从后端加载所有节点
      await loadNodesFromBackend()
    }
    initializeNodes()
  }, [])
}
```

### 2. 节点加载
```typescript
// backendNodeLoader.ts
export async function loadNodesFromBackend() {
  // 1. 获取节点列表
  const response = await nodesAPI.list()
  
  // 2. 获取每个节点的详细信息
  for (const item of response.nodes) {
    const nodeInfo = await nodesAPI.getInfo(item.node_type)
    
    // 3. 转换为前端NodeDefinition
    const definition = convertBackendNodeToDefinition(nodeInfo)
    
    // 4. 注册到前端registry
    registry.register(definition)
  }
}
```

### 3. UI映射规则
```typescript
// 后端只提供category和tags
const nodeInfo = {
  category: "ai",
  tags: ["code", "coder"]
}

// 前端自动映射UI配置
const uiConfig = {
  icon: Code,        // 根据tags选择
  color: "#8B5CF6",  // 根据category选择
  displayName: "AI智能"
}
```

### 4. 工作流执行
```typescript
// Toolbar.tsx
const handleRun = async () => {
  // 调用后端API执行整个工作流
  const result = await workflowAPI.execute(nodes, edges)
  
  // 更新节点输出数据
  Object.entries(result.results).forEach(([nodeId, nodeResult]) => {
    updateNodeData(nodeId, { attributes: nodeResult.outputs })
  })
}
```

## API接口

### 节点相关
- `GET /api/v1/nodes` - 获取所有节点列表
- `GET /api/v1/nodes/{node_type}` - 获取节点详细信息
- `POST /api/v1/nodes/{node_type}/execute` - 执行单个节点（已废弃）

### 工作流相关
- `POST /api/v1/workflows/execute` - 执行工作流

## 后端节点示例

```python
from deepeye.nodes import BaseNode, NodeMetadata, register_node

@register_node
class DataCoderNode(BaseNode):
    node_type = "DataCoder"
    
    def __init__(self, node_id=None, config=None):
        super().__init__(node_id, config)
        
        # 设置元数据
        self.metadata = NodeMetadata(
            name="DataCoder",
            display_name="智能数据处理器",
            description="使用LLM将自然语言转换为Python代码",
            category="ai",  # 前端会映射为紫色AI图标
            tags=["llm", "code", "coder"],
            version="0.1.0"
        )
```

## 分类映射

| Category | 图标 | 颜色 | 显示名称 |
|----------|------|------|----------|
| datasource | Database | #3B82F6 | 数据源 |
| ai | Sparkles | #8B5CF6 | AI智能 |
| logic | GitBranch | #10B981 | 逻辑 |
| math | Calculator | #F59E0B | 数学 |
| text | Type | #EC4899 | 文本 |
| data | Filter | #06B6D4 | 数据处理 |
| debug | Bug | #EF4444 | 调试 |
| general | Sparkles | #6B7280 | 通用 |

## 注意事项

1. **不要在前端定义节点**：所有节点都应该在后端定义
2. **装饰器系统已废弃**：`@Node`、`@Input`、`@Output`等装饰器仅保留以备将来使用
3. **执行器已废弃**：`SimpleExecutor`和`BackendNodeExecutor`已删除，使用`workflowAPI.execute()`
4. **UI配置自动映射**：后端只需提供`category`和`tags`，前端自动选择图标和颜色

