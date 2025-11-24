/**
 * ImageViewer 节点的视图组件
 */

import { ImageGalleryView } from '@/nodes/components/shared/ImageGalleryView'
import type { NodeViewProps } from '@/nodes/types'

export const ImageViewerView = ({ attributes }: NodeViewProps) => {
  const images = attributes?.output_images || []

  // 调试日志
  console.log('🖼️ ImageViewerView 渲染:', {
    attributes,
    images,
    imageCount: images.length,
    firstImage: images[0] ? {
      filename: images[0].filename,
      format: images[0].format,
      dataLength: images[0].data?.length,
      dataPreview: images[0].data?.substring(0, 50)
    } : null
  })

  return <ImageGalleryView images={images} label="图片预览" maxImages={10} />
}

