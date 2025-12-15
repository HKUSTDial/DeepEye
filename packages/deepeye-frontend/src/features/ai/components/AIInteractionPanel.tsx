/**
 * AI 交互面板组件
 *
 * 简洁的 AI 输入面板，显示在节点下方
 * 设计风格：参照截图 - 深色专业风格
 *
 * AI 逻辑由后端处理，前端只负责 UI 和消息传递
 */

import { useState, useRef } from 'react'
import { Send, Sparkles } from 'lucide-react'
import { ModelSelector } from '@/shared/components'

export interface AIInteractionPanelProps {
  /** 消息发送回调（发送到后端） */
  onMessage: (message: string, modelId?: string) => Promise<string>
  /** 输入框占位符 */
  placeholder?: string
  /** 默认模型 ID */
  defaultModel?: string
}

export function AIInteractionPanel({
  onMessage,
  placeholder = '输入指令...',
  defaultModel
}: AIInteractionPanelProps) {
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [response, setResponse] = useState<string>('')
  const [selectedModel, setSelectedModel] = useState(defaultModel || '')
  const inputRef = useRef<HTMLInputElement>(null)

  // 处理发送
  const handleSubmit = async () => {
    if (!input.trim() || isLoading) return

    const userInput = input.trim()
    setInput('')
    setIsLoading(true)
    setResponse('')

    try {
      // 调用后端 API，传递选中的模型
      const aiResponse = await onMessage(userInput, selectedModel)
      setResponse(aiResponse)

      console.log('✅ AI 响应:', aiResponse)
    } catch (error) {
      console.error('❌ AI 请求失败:', error)
      setResponse('请求失败，请稍后重试')
    } finally {
      setIsLoading(false)
    }
  }

  // 处理键盘事件
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div
      className="absolute left-1/2 -translate-x-1/2 mt-2 z-50"
      style={{
        top: '100%',
        minWidth: '400px',
        maxWidth: '500px',
        width: 'max-content'
      }}
    >
      {/* 主容器 */}
      <div className="bg-card rounded-lg border shadow-[0_8px_32px_rgba(0,0,0,0.4)] overflow-hidden w-full">
        {/* 顶部控制栏 */}
        <div className="px-3 py-2 bg-card border-b border flex items-center gap-2">
          {/* AI 模型选择 */}
          <div className="flex items-center gap-2 flex-1">
            <span className="text-xs text-muted-foreground">模型:</span>
            <ModelSelector
              value={selectedModel}
              onChange={setSelectedModel}
              groupByProvider={true}
            />
          </div>

          {/* 右侧按钮组 */}
          <div className="flex items-center gap-1.5">
            <button className="p-1.5 bg-background hover:bg-secondary border text-foreground rounded transition-colors">
              <Sparkles className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* 响应区域 */}
        {response && (
          <div className="px-3 py-2 bg-background border-b border">
            <div className="text-sm text-foreground">
              {response}
            </div>
          </div>
        )}

        {/* 输入区域 */}
        <div className="p-3 bg-card">
          <div className="relative">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              className="w-full px-4 py-2.5 pr-12 text-sm rounded-lg bg-background border text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-all"
              disabled={isLoading}
            />
            <button
              onClick={handleSubmit}
              disabled={isLoading || !input.trim()}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 bg-primary hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed text-primary-foreground rounded transition-all active:scale-95"
              title="发送 (Enter)"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
