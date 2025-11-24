/**
 * UnifiedNode - 统一节点组件
 *
 * 使用模块化组件构建，支持：
 * - 节点头部（图标、标签、颜色）
 * - 数据视图（@ViewData 装饰器标记的属性）
 * - 输入端口（左侧）
 * - 输出端口（右侧）
 * - 自定义视图（可选）
 * - AI 交互面板（AI 节点选中时显示）
 */

import { memo, useState, useEffect } from 'react'
import { NodeProps, useReactFlow } from 'reactflow'
import { registry } from '@/nodes/registry'
import { cn } from '@/shared/utils'
import { LucideIcon } from 'lucide-react'
import { NodeHeader, NodePorts, NodeView } from './shared'
import { DataTableView } from './shared/DataTableView'
import { AIInteractionPanel } from '@/features/ai/components'
import { useGraphStore } from '@/store'
import { SimpleExecutor } from '@/nodes/execution'


// ============================================================================
// 组件
// ============================================================================

interface UnifiedNodeProps extends NodeProps {
  data: {
    label?: string
    attributes?: Record<string, any>
  }
}

export const UnifiedNode = memo(({ id, type, data, selected }: UnifiedNodeProps) => {
  // 从注册表获取节点定义
  const nodeType = type || (data as any).type || ''
  const definition = registry.get(nodeType)

  // AI 面板显示状态
  const [showAIPanel, setShowAIPanel] = useState(false)
  const updateNodeData = useGraphStore(state => state.updateNodeData)
  const addNodeHistory = useGraphStore(state => state.addNodeHistory)

  // 获取 React Flow 实例
  const { getNodes, getEdges } = useReactFlow()

  // 监听选中状态，控制 AI 面板显示
  useEffect(() => {
    if (definition?.aiConfig) {
      setShowAIPanel(selected || false)
    }
  }, [selected, definition?.aiConfig])

  if (!definition) {
    return (
      <div className="px-4 py-2 rounded border-2 border-destructive bg-destructive/10">
        <div className="text-xs text-destructive">
          Unknown node type: {nodeType}
        </div>
      </div>
    )
  }

  // 获取 ViewData 配置（从 definition 中直接获取）
  const viewDataConfigs = definition.viewData || {}
  const hasViewData = Object.keys(viewDataConfigs).length > 0

  // 获取节点属性数据
  const attributes = data?.attributes || {}

  // 处理 AI 消息
  const handleAIMessage = async (message: string, modelId?: string) => {
    console.log('📤 AI 消息:', message, '模型:', modelId)

    try {
      // 1. 获取上游节点的输入数据
      const nodes = getNodes()
      const edges = getEdges()
      const executor = new SimpleExecutor(nodes, edges)

      console.log('🔄 获取上游输入数据...')
      const nodeInputs = await executor.getNodeInputs(id!)

      console.log('✅ 输入数据获取完成:', nodeInputs)

      // 2. 创建节点实例
      const instance = new definition.class()

      // 3. 设置节点属性（包括从上游获取的输入数据）
      Object.assign(instance, nodeInputs)

      // 4. 如果节点有 model 属性，设置选中的模型
      if (modelId && 'model' in instance) {
        instance.model = modelId
      }

      // 5. 调用节点的 handleAIRequest 方法
      if (typeof instance.handleAIRequest === 'function') {
        const response = await instance.handleAIRequest(message, modelId)

        console.log('📝 handleAIRequest 执行完成，节点实例状态:')
        console.log('  - sql:', instance.sql)
        console.log('  - data:', instance.data)
        console.log('  - explanation:', instance.explanation)

        // 6. 更新节点数据
        const updatedAttributes = { ...attributes }

        // 更新所有输出端口的值
        Object.keys(definition.outputs).forEach(key => {
          if (key in instance) {
            console.log(`  - 更新输出端口 ${key}:`, instance[key])
            updatedAttributes[key] = instance[key]
          }
        })

        // 如果节点有 model 属性，也保存到 attributes
        if (modelId && 'model' in instance) {
          updatedAttributes.model = modelId
        }

        console.log('💾 更新节点 attributes:', updatedAttributes)
        updateNodeData(id!, { attributes: updatedAttributes })

        // 7. 保存到历史记录
        const outputs: Record<string, any> = {}
        Object.keys(definition.outputs).forEach(key => {
          if (key in instance) {
            outputs[key] = instance[key]
          }
        })

        addNodeHistory(id!, {
          type: 'ai_request',
          inputs: nodeInputs,
          outputs: outputs,
          config: { model: modelId },
          prompt: message,
          modelId: modelId,
          success: true,
        })

        // 8. 清除下游节点缓存
        executor.invalidateCache(id!)

        // 9. 返回响应消息
        return response?.content || '✅ 处理完成'
      } else {
        throw new Error('节点未实现 handleAIRequest 方法')
      }
    } catch (error: any) {
      console.error('❌ AI 请求失败:', error)

      // 保存失败记录到历史
      addNodeHistory(id!, {
        type: 'ai_request',
        inputs: {},
        outputs: {},
        config: { model: modelId },
        prompt: message,
        modelId: modelId,
        success: false,
        error: error.message,
      })

      return `❌ 错误: ${error.message}`
    }
  }

  return (
    <div
      className={cn(
        'node-container relative overflow-visible',
        'rounded-lg border-2',
        selected && 'node-container-selected'
      )}
      style={{
        minWidth: '180px',
        maxWidth: '300px',
      }}
    >
      {/* 节点头部 */}
      <NodeHeader
        label={definition.label}
        icon={definition.icon as LucideIcon | undefined}
        color={definition.color}
        selected={selected}
      />

      {/* 数据视图区域（@ViewData 装饰器标记的属性） */}
      {hasViewData && (
        <div className="border-b border">
          {Object.entries(viewDataConfigs).map(([propertyKey, config]) => {
            let dataValue = attributes[propertyKey]

            // 如果数据包含 dataframe 字段，提取它（处理后端返回的包装格式）
            if (dataValue && typeof dataValue === 'object' && dataValue.dataframe) {
              dataValue = dataValue.dataframe
            }

            console.log(`🔍 ViewData [${propertyKey}]:`, {
              config,
              dataValue,
              originalValue: attributes[propertyKey],
              allAttributes: attributes
            })
            return (
              <DataTableView
                key={propertyKey}
                data={dataValue}
                label={config.label}
                maxRows={config.maxRows}
                showIndex={config.showIndex}
              />
            )
          })}
        </div>
      )}

      {/* 自定义视图区域 */}
      <NodeView view={definition.view} nodeData={data} />

      {/* 端口区域 */}
      <NodePorts
        inputs={definition.inputs}
        outputs={definition.outputs}
      />

      {/* AI 交互面板 - 显示在节点下方 */}
      {showAIPanel && definition.aiConfig && (
        <AIInteractionPanel
          onMessage={handleAIMessage}
          placeholder={definition.aiConfig.placeholder}
        />
      )}
    </div>
  )
})

UnifiedNode.displayName = 'UnifiedNode'

