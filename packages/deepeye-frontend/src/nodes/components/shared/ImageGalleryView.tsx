/**
 * 图片画廊视图组件
 *
 * 用于显示图片数据（base64 格式）
 */

import { cn } from '@/shared/utils'
import { useState } from 'react'
import { createPortal } from 'react-dom'
import { AlertCircle, X, Download } from 'lucide-react'

export interface ImageGalleryViewProps {
  /** 图片数据列表 */
  images: Array<{
    data: string // base64 字符串
    filename?: string
    description?: string
    format?: string
    file_size?: number
  }>
  /** 显示标签 */
  label?: string
  /** 最大显示数量 */
  maxImages?: number
}

export function ImageGalleryView({
  images,
  label,
  maxImages = 10
}: ImageGalleryViewProps) {
  const [previewIndex, setPreviewIndex] = useState<number | null>(null)
  const [loadErrors, setLoadErrors] = useState<Set<number>>(new Set())

  // 如果没有图片，显示空状态
  if (!images || images.length === 0) {
    return (
      <div className="px-3 py-2 text-xs text-muted-foreground text-center">
        {label ? `${label}: ` : ''}暂无图片
      </div>
    )
  }

  const displayImages = images.slice(0, maxImages)
  const hasMore = images.length > maxImages

  // 处理图片加载错误
  const handleImageError = (idx: number) => {
    setLoadErrors(prev => new Set(prev).add(idx))
  }

  // 格式化文件大小
  const formatFileSize = (bytes?: number) => {
    if (!bytes) return ''
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  // 关闭预览
  const closePreview = () => setPreviewIndex(null)

  // 下载图片
  const downloadImage = (image: typeof images[0], idx: number) => {
    const link = document.createElement('a')
    link.href = `data:image/${image.format || 'png'};base64,${image.data}`
    link.download = image.filename || `image_${idx + 1}.${image.format || 'png'}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <>
      <div className="w-full">
        {label && (
          <div className="px-3 py-1.5 text-xs font-medium text-muted-foreground bg-secondary/50 border-b">
            {label} ({images.length} 张)
          </div>
        )}

        <div className="p-2 space-y-2 max-h-[400px] overflow-y-auto">
          {displayImages.map((image, idx) => {
            const hasError = loadErrors.has(idx)
            const imageUrl = `data:image/${image.format || 'png'};base64,${image.data}`

            return (
              <div
                key={idx}
                className={cn(
                  'border rounded-lg overflow-hidden bg-background',
                  'transition-all duration-200 hover:border-primary/50',
                  hasError && 'border-destructive'
                )}
              >
                {/* 图片信息头部 */}
                <div className="px-2 py-1.5 bg-secondary/30 border-b">
                  <div className="text-xs font-medium text-foreground truncate">
                    {image.filename || `image_${idx + 1}.${image.format || 'png'}`}
                  </div>
                  {image.description && (
                    <div className="text-xs text-muted-foreground truncate">
                      {image.description}
                    </div>
                  )}
                  {image.file_size && (
                    <div className="text-xs text-muted-foreground">
                      {formatFileSize(image.file_size)}
                    </div>
                  )}
                </div>

                {/* 图片缩略图 */}
                <div className="p-2 bg-secondary/10 flex items-center justify-center max-h-[150px]">
                  {hasError ? (
                    <div className="flex flex-col items-center gap-2 text-destructive">
                      <AlertCircle className="w-8 h-8" />
                      <div className="text-xs">图片加载失败</div>
                    </div>
                  ) : (
                    <img
                      src={imageUrl}
                      alt={image.description || image.filename || `Image ${idx + 1}`}
                      className="max-w-full max-h-[130px] object-contain rounded cursor-pointer hover:opacity-80 transition-opacity"
                      onClick={() => setPreviewIndex(idx)}
                      onError={() => handleImageError(idx)}
                    />
                  )}
                </div>
              </div>
            )
          })}
        </div>

        {/* 更多图片提示 */}
        {hasMore && (
          <div className="px-2 py-1 text-center text-muted-foreground bg-secondary/20 text-xs border-t">
            还有 {images.length - maxImages} 张图片...
          </div>
        )}
      </div>

      {/* 图片预览弹窗 - 使用 Portal 渲染到 body，避免被节点容器限制 */}
      {previewIndex !== null && createPortal(
        <div
          className="fixed inset-0 z-[9999] bg-black/90 flex"
          onClick={closePreview}
        >
          {/* 左侧：图片显示区域 */}
          <div className="flex-1 flex items-center justify-center p-8">
            <img
              src={`data:image/${images[previewIndex].format || 'png'};base64,${images[previewIndex].data}`}
              alt={images[previewIndex].description || images[previewIndex].filename || `Image ${previewIndex + 1}`}
              className="max-w-full max-h-full object-contain"
              onClick={(e) => e.stopPropagation()}
            />
          </div>

          {/* 右侧：信息面板 */}
          <div
            className="w-80 bg-background border-l border-border flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* 顶部操作栏 */}
            <div className="flex items-center justify-between p-4 border-b border-border">
              <h3 className="text-sm font-medium text-foreground">图片详情</h3>
              <div className="flex items-center gap-2">
                {/* 下载按钮 */}
                <button
                  onClick={() => downloadImage(images[previewIndex], previewIndex)}
                  className="p-2 rounded hover:bg-secondary transition-colors"
                  title="下载图片"
                >
                  <Download className="w-4 h-4" />
                </button>
                {/* 关闭按钮 */}
                <button
                  onClick={closePreview}
                  className="p-2 rounded hover:bg-secondary transition-colors"
                  title="关闭"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* 图片信息内容 */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* 文件名 */}
              <div>
                <div className="text-xs text-muted-foreground mb-1">文件名</div>
                <div className="text-sm text-foreground break-all">
                  {images[previewIndex].filename || `image_${previewIndex + 1}.${images[previewIndex].format || 'png'}`}
                </div>
              </div>

              {/* 描述 */}
              {images[previewIndex].description && (
                <div>
                  <div className="text-xs text-muted-foreground mb-1">描述</div>
                  <div className="text-sm text-foreground">
                    {images[previewIndex].description}
                  </div>
                </div>
              )}

              {/* 文件大小 */}
              {images[previewIndex].file_size && (
                <div>
                  <div className="text-xs text-muted-foreground mb-1">文件大小</div>
                  <div className="text-sm text-foreground">
                    {formatFileSize(images[previewIndex].file_size)}
                  </div>
                </div>
              )}

              {/* 格式 */}
              <div>
                <div className="text-xs text-muted-foreground mb-1">格式</div>
                <div className="text-sm text-foreground uppercase">
                  {images[previewIndex].format || 'png'}
                </div>
              </div>

              {/* 图片索引 */}
              <div>
                <div className="text-xs text-muted-foreground mb-1">位置</div>
                <div className="text-sm text-foreground">
                  {previewIndex + 1} / {images.length}
                </div>
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  )
}

