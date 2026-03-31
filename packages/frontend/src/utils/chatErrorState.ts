export interface ChatErrorState {
  title: string
  summary: string
  suggestion: string
}

function containsAny(value: string, patterns: string[]) {
  return patterns.some((pattern) => value.includes(pattern))
}

export function deriveChatErrorState(error: string): ChatErrorState {
  const normalized = error.trim().toLowerCase()

  if (containsAny(normalized, ['connection lost', 'failed to fetch', 'networkerror'])) {
    return {
      title: 'Connection interrupted',
      summary: 'DeepEye lost contact with the backend before the reply finished.',
      suggestion: 'Retry the last request or wait for the connection to recover.',
    }
  }

  if (containsAny(normalized, ['failed to create session'])) {
    return {
      title: 'Could not start a new thread',
      summary: 'The assistant could not create a session for this request.',
      suggestion: 'Try again in a moment. If it keeps failing, refresh the page.',
    }
  }

  if (containsAny(normalized, ['backend is not ready', 'bad gateway', '502'])) {
    return {
      title: 'Backend is still starting',
      summary: 'The request reached DeepEye, but the service handling it was not ready.',
      suggestion: 'Wait a few seconds, then retry the request.',
    }
  }

  if (containsAny(normalized, ['timed out', 'timeout'])) {
    return {
      title: 'The request timed out',
      summary: 'The run took too long and stopped before a final answer was ready.',
      suggestion: 'Retry the request or narrow the scope of the task.',
    }
  }

  return {
    title: 'The reply stopped before completion',
    summary: 'DeepEye hit an issue while generating the response.',
    suggestion: 'Retry the request or inspect the workflow details for the failing step.',
  }
}
