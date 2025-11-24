/**
 * ImageViewer 节点 - 图片显示器
 * 显示图片数据
 */

import { Node } from '@/nodes/decorators'
import { Image } from 'lucide-react'
import { ImageViewerView } from './ImageViewerView'

@Node({
  type: 'visualization.imageviewer',
  label: '图片显示器',
  category: 'visualization',
  icon: Image,
  color: '#10B981',
  inputs: {
    images: {
      type: 'array',
      label: '图片列表',
      description: '图片列表（PNG/JPG 等格式）',
      required: true
    }
  },
  outputs: {
    output_images: {
      type: 'array',
      label: '图片列表',
      description: '原样输出图片列表'
    }
  },
  view: {
    component: ImageViewerView
  }
})
export class ImageViewerNode {
  images: any[] = []
  output_images: any[] = []

  async compute() {
    // ImageViewer 是纯前端节点，不需要调用后端
    // 直接将输入的图片数据传递到输出
    if (!this.images || this.images.length === 0) {
      throw new Error('请先连接图片数据源（images 输入端口）')
    }

    // 原样输出图片数据
    this.output_images = this.images
  }
}

