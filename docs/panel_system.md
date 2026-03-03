# Panel 系统说明（详细版）

## 作用
Panel 系统负责右侧多面板管理与渲染，支撑 Workflow Live Panel、Files Panel 等独立功能区。

## 架构设计

1) 面板注册  
路径：`packages/frontend/src/components/right-panel/panelRegistry.tsx`  
说明：  
`panelRegistry` 维护所有可用面板（id、label、render）。  

2) 布局管理  
路径：`packages/frontend/src/components/right-panel/RightPanelLayout.tsx`  
说明：  
负责 tabs、split panes、多面板渲染与切换。

3) 状态存储  
路径：`packages/frontend/src/stores/rightPanel.ts`  
说明：  
保存面板布局与激活状态，支持多 panes、tab 复用。  

## 核心功能类说明

- `useRightPanelStore`  
  - 维护 panes/tabs  
  - 提供 openTab/openOrFocusTab  
  - 支持 splitPane/closePane  

- `panelRegistry`  
  - 定义面板插件  
  - 统一扩展入口  

- `WorkflowLivePanel`  
  - 订阅 workflow_event  
  - 动画渲染节点与连线  
  - 展示运行状态与输出  

- `FilesPanel`  
  - 读取 sandbox 文件列表  
  - 支持拖拽与预览  

## 扩展方式

### 示例：新增日志面板

1) 创建组件
```tsx
// packages/frontend/src/components/right-panel/plugins/LogsPanel.tsx
export function LogsPanel() {
  return <div className="p-4 text-sm text-slate-300">Logs Panel</div>
}
```

2) 注册到 panelRegistry
```tsx
// packages/frontend/src/components/right-panel/panelRegistry.tsx
import { LogsPanel } from './plugins/LogsPanel'

panelRegistry.push({
  id: 'logs',
  label: 'Logs',
  render: () => <LogsPanel />,
})
```

3) 触发打开
```ts
openOrFocusTab('logs')
```

