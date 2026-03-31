import type { AppLocale } from '../locale'

export interface ChatErrorState {
  title: string
  summary: string
  suggestion: string
}

function containsAny(value: string, patterns: string[]) {
  return patterns.some((pattern) => value.includes(pattern))
}

function buildState(locale: AppLocale, key: string): ChatErrorState {
  const isZh = locale === 'zh-CN'

  if (key === 'connection') {
    return isZh
      ? {
          title: '连接已中断',
          summary: 'DeepEye 在回复完成前与后端失去了连接。',
          suggestion: '请重试上一条请求，或等待连接恢复后再继续。',
        }
      : {
          title: 'Connection interrupted',
          summary: 'DeepEye lost contact with the backend before the reply finished.',
          suggestion: 'Retry the last request or wait for the connection to recover.',
        }
  }

  if (key === 'create-session') {
    return isZh
      ? {
          title: '无法创建新线程',
          summary: '这次请求没能成功创建会话。',
          suggestion: '稍后再试一次。如果持续失败，请刷新页面。',
        }
      : {
          title: 'Could not start a new thread',
          summary: 'The assistant could not create a session for this request.',
          suggestion: 'Try again in a moment. If it keeps failing, refresh the page.',
        }
  }

  if (key === 'backend') {
    return isZh
      ? {
          title: '后端仍在启动中',
          summary: '请求已经到达 DeepEye，但对应服务还没准备好。',
          suggestion: '稍等几秒后再重试。',
        }
      : {
          title: 'Backend is still starting',
          summary: 'The request reached DeepEye, but the service handling it was not ready.',
          suggestion: 'Wait a few seconds, then retry the request.',
        }
  }

  if (key === 'timeout') {
    return isZh
      ? {
          title: '请求超时了',
          summary: '本次运行耗时过长，在生成最终答复前停止了。',
          suggestion: '请重试，或者缩小这次任务的范围。',
        }
      : {
          title: 'The request timed out',
          summary: 'The run took too long and stopped before a final answer was ready.',
          suggestion: 'Retry the request or narrow the scope of the task.',
        }
  }

  return isZh
    ? {
        title: '回复未能完整生成',
        summary: 'DeepEye 在生成回复时遇到了问题。',
        suggestion: '请重试，或打开工作流检查失败步骤。',
      }
    : {
        title: 'The reply stopped before completion',
        summary: 'DeepEye hit an issue while generating the response.',
        suggestion: 'Retry the request or inspect the workflow details for the failing step.',
      }
}

export function deriveChatErrorState(error: string, locale: AppLocale = 'en'): ChatErrorState {
  const normalized = error.trim().toLowerCase()

  if (containsAny(normalized, ['connection lost', 'failed to fetch', 'networkerror'])) {
    return buildState(locale, 'connection')
  }

  if (containsAny(normalized, ['failed to create session'])) {
    return buildState(locale, 'create-session')
  }

  if (containsAny(normalized, ['backend is not ready', 'bad gateway', '502'])) {
    return buildState(locale, 'backend')
  }

  if (containsAny(normalized, ['timed out', 'timeout'])) {
    return buildState(locale, 'timeout')
  }

  return buildState(locale, 'generic')
}
