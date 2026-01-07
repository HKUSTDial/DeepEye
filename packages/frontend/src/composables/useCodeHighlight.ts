import { ref } from 'vue'
import { createHighlighter, type Highlighter, type BundledLanguage } from 'shiki'

let highlighterInstance: Highlighter | null = null
const isInitializing = ref(false)
const isReady = ref(false)

export function useCodeHighlight() {
  async function initHighlighter() {
    if (highlighterInstance) return highlighterInstance
    if (isInitializing.value) {
      // Wait for initialization
      while (isInitializing.value) {
        await new Promise(resolve => setTimeout(resolve, 50))
      }
      return highlighterInstance
    }

    isInitializing.value = true
    try {
      highlighterInstance = await createHighlighter({
        themes: ['github-dark', 'github-light'],
        langs: [
          'python',
          'javascript',
          'typescript',
          'json',
          'html',
          'css',
          'bash',
          'yaml',
          'xml',
          'sql',
          'markdown',
          'vue',
          'jsx',
          'tsx',
        ],
      })
      isReady.value = true
      return highlighterInstance
    } finally {
      isInitializing.value = false
    }
  }

  function getLanguage(ext?: string): BundledLanguage {
    const languageMap: Record<string, BundledLanguage> = {
      py: 'python',
      js: 'javascript',
      ts: 'typescript',
      jsx: 'jsx',
      tsx: 'tsx',
      json: 'json',
      html: 'html',
      css: 'css',
      xml: 'xml',
      yaml: 'yaml',
      yml: 'yaml',
      md: 'markdown',
      vue: 'vue',
      sh: 'bash',
      bash: 'bash',
      sql: 'sql',
    }

    return (languageMap[ext || ''] as BundledLanguage) || 'plaintext'
  }

  async function highlight(code: string, ext?: string): Promise<string> {
    const highlighter = await initHighlighter()
    if (!highlighter) {
      return `<pre><code>${escapeHtml(code)}</code></pre>`
    }

    const lang = getLanguage(ext)
    
    try {
      let html = highlighter.codeToHtml(code, {
        lang,
        theme: 'github-dark',
      })
      // Remove whitespace/newlines between </span> and <span class="line">
      // This prevents double line spacing in <pre> tags
      html = html.replace(/<\/span>\s*<span class="line">/g, '</span><span class="line">')
      return html
    } catch (error) {
      console.error('Syntax highlighting error:', error)
      return `<pre><code>${escapeHtml(code)}</code></pre>`
    }
  }

  function escapeHtml(text: string): string {
    const div = document.createElement('div')
    div.textContent = text
    return div.innerHTML
  }

  return {
    highlight,
    isReady,
    isInitializing,
  }
}

