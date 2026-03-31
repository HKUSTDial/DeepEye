import { useState, useCallback } from 'react'

type SupportedTheme = 'github-dark' | 'github-light'

const THEME_LOADERS = {
  'github-dark': () => import('shiki/dist/themes/github-dark.mjs'),
  'github-light': () => import('shiki/dist/themes/github-light.mjs'),
} as const

const LANGUAGE_LOADERS = {
  python: () => import('shiki/dist/langs/python.mjs'),
  javascript: () => import('shiki/dist/langs/javascript.mjs'),
  typescript: () => import('shiki/dist/langs/typescript.mjs'),
  json: () => import('shiki/dist/langs/json.mjs'),
  html: () => import('shiki/dist/langs/html.mjs'),
  css: () => import('shiki/dist/langs/css.mjs'),
  bash: () => import('shiki/dist/langs/bash.mjs'),
  yaml: () => import('shiki/dist/langs/yaml.mjs'),
  xml: () => import('shiki/dist/langs/xml.mjs'),
  sql: () => import('shiki/dist/langs/sql.mjs'),
  markdown: () => import('shiki/dist/langs/markdown.mjs'),
  vue: () => import('shiki/dist/langs/vue.mjs'),
  jsx: () => import('shiki/dist/langs/jsx.mjs'),
  tsx: () => import('shiki/dist/langs/tsx.mjs'),
} as const

type SupportedLanguage = keyof typeof LANGUAGE_LOADERS

type HighlightHighlighter = {
  loadTheme: (...themes: SupportedTheme[]) => Promise<void>
  loadLanguage: (...langs: SupportedLanguage[]) => Promise<void>
  codeToHtml: (code: string, options: { lang: SupportedLanguage; theme: SupportedTheme }) => string
}

type HighlightRuntime = {
  createHighlighter: (options: {
    themes: SupportedTheme[]
    langs: SupportedLanguage[]
    warnings?: boolean
  }) => Promise<HighlightHighlighter>
}

let highlighterInstance: HighlightHighlighter | null = null
let initPromise: Promise<HighlightHighlighter> | null = null
let runtimePromise: Promise<HighlightRuntime> | null = null
const loadedLanguages = new Set<SupportedLanguage>()
const loadedThemes = new Set<SupportedTheme>()

async function loadHighlightRuntime(): Promise<HighlightRuntime> {
  if (!runtimePromise) {
    runtimePromise = Promise.all([
      import('shiki/core'),
      import('shiki/engine/javascript'),
    ]).then(([core, engine]) => ({
      createHighlighter: core.createBundledHighlighter<SupportedLanguage, SupportedTheme>({
        langs: LANGUAGE_LOADERS,
        themes: THEME_LOADERS,
        engine: engine.createJavaScriptRegexEngine,
      }),
    }))
  }
  return runtimePromise
}

function resolveLanguage(ext?: string): SupportedLanguage | null {
  const languageMap: Record<string, SupportedLanguage> = {
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

  return languageMap[ext || ''] || null
}

function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

async function ensureLanguageLoaded(highlighter: HighlightHighlighter, lang: SupportedLanguage) {
  if (loadedLanguages.has(lang)) return
  await highlighter.loadLanguage(lang)
  loadedLanguages.add(lang)
}

async function ensureThemeLoaded(highlighter: HighlightHighlighter, theme: SupportedTheme) {
  if (loadedThemes.has(theme)) return
  await highlighter.loadTheme(theme)
  loadedThemes.add(theme)
}

export function useCodeHighlight() {
  const [isReady, setIsReady] = useState(Boolean(highlighterInstance))
  const [isInitializing, setIsInitializing] = useState(false)

  const initHighlighter = useCallback(async () => {
    if (highlighterInstance) return highlighterInstance

    if (initPromise) {
      return initPromise
    }

    setIsInitializing(true)

    initPromise = loadHighlightRuntime()
      .then(({ createHighlighter }) => createHighlighter({
        themes: [],
        langs: [],
        warnings: false,
      }))
      .then((highlighter) => {
        highlighterInstance = highlighter
        setIsReady(true)
        setIsInitializing(false)
        return highlighter
      })
      .catch((error) => {
        setIsInitializing(false)
        initPromise = null
        throw error
      })

    return initPromise
  }, [])

  const highlight = useCallback(async (code: string, ext?: string): Promise<string> => {
    const lang = resolveLanguage(ext)
    if (!lang) {
      return `<pre><code>${escapeHtml(code)}</code></pre>`
    }

    const theme: SupportedTheme = document.body.classList.contains('dark-theme')
      ? 'github-dark'
      : 'github-light'

    try {
      const highlighter = await initHighlighter()
      await Promise.all([
        ensureLanguageLoaded(highlighter, lang),
        ensureThemeLoaded(highlighter, theme),
      ])

      let html = highlighter.codeToHtml(code, { lang, theme })
      html = html.replace(/<\/span>\s*<span class="line">/g, '</span><span class="line">')
      return html
    } catch (error) {
      console.error('Syntax highlighting error:', error)
      return `<pre><code>${escapeHtml(code)}</code></pre>`
    }
  }, [initHighlighter])

  return {
    highlight,
    isReady,
    isInitializing,
  }
}
