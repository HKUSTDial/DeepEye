import { useState } from 'react'
import { EdgeProps, getBezierPath } from 'reactflow'
import { useThemeStore } from '@/store/themeStore'

export function CustomEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
  selected,
}: EdgeProps) {
  const theme = useThemeStore((state) => state.theme)
  const isDark = theme === 'dark'
  const [isHovered, setIsHovered] = useState(false)
  
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  })

  // 根据主题和状态设置颜色
  const getStrokeColor = () => {
    if (selected) {
      // 选中状态：使用主题色（iOS 蓝色）
      return '#007AFF'
    }
    if (isHovered) {
      // Hover状态：更明显的颜色
      return isDark ? 'hsl(0 0% 60%)' : 'hsl(0 0% 50%)'
    }
    // 未选中状态：根据主题使用不同颜色
    return isDark ? 'hsl(0 0% 40%)' : 'hsl(0 0% 75%)'
  }

  // 合并默认样式和自定义样式
  const finalStyle = {
    // 默认样式
    stroke: getStrokeColor(),
    strokeWidth: selected ? 2.5 : isHovered ? 2 : 1.5,
    opacity: selected ? 1 : isHovered ? 0.9 : 0.7,
    transition: 'stroke 0.2s ease, stroke-width 0.2s ease, opacity 0.2s ease',
    // 自定义样式（会覆盖默认样式）
    ...style,
  }

  return (
    <>
      {/* 不可见的宽边缘，用于更容易触发hover */}
      <path
        d={edgePath}
        fill="none"
        strokeWidth={20}
        stroke="transparent"
        style={{ cursor: 'pointer' }}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      />
      {/* 实际可见的边 */}
      <path
        id={id}
        className="react-flow__edge-path"
        d={edgePath}
        fill="none"
        markerEnd={markerEnd}
        style={{
          ...finalStyle,
          pointerEvents: 'none', // 让上面的透明边处理交互
        }}
      />
    </>
  )
}

