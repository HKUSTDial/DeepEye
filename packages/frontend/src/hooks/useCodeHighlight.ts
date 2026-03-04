import { useState, useCallback } from 'react'
import { createHighlighter, type Highlighter, type BundledLanguage } from 'shiki'

let highlighterInstance: Highlighter | null = null
let initPromise: Promise<Highlighter> | null = null

export function useCodeHighlight() {
  const [isReady, setIsReady] = useState(Boolean(highlighterInstance))
  const [isInitializing, setIsInitializing] = useState(false)

  const initHighlighter = useCallback(async () => {
    if (highlighterInstance) return highlighterInstance
    
    if (initPromise) {
      return initPromise
    }

    setIsInitializing(true)
    
    initPromise = createHighlighter({
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
    }).then((h) => {
      highlighterInstance = h
      setIsReady(true)
      setIsInitializing(false)
      return h
    }).catch((e) => {
      setIsInitializing(false)
      initPromise = null
      throw e
    })

    return initPromise
  }, [])

  const getLanguage = useCallback((ext?: string): BundledLanguage => {
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
  }, [])

  const escapeHtml = useCallback((text: string): string => {
    const div = document.createElement('div')
    div.textContent = text
    return div.innerHTML
  }, [])

  const highlight = useCallback(async (code: string, ext?: string): Promise<string> => {
    const highlighter = await initHighlighter()
    if (!highlighter) {
      return `<pre><code>${escapeHtml(code)}</code></pre>`
    }

    const lang = getLanguage(ext)
    const theme = document.body.classList.contains('dark-theme') ? 'github-dark' : 'github-light'
    
    try {
      let html = highlighter.codeToHtml(code, {
        lang,
        theme,
      })
      // Remove whitespace/newlines between </span> and <span class="line">
      // This prevents double line spacing in <pre> tags
      html = html.replace(/<\/span>\s*<span class="line">/g, '</span><span class="line">')
      return html
    } catch (error) {
      console.error('Syntax highlighting error:', error)
      return `<pre><code>${escapeHtml(code)}</code></pre>`
    }
  }, [initHighlighter, getLanguage, escapeHtml])

  return {
    highlight,
    isReady,
    isInitializing,
  }
}
