import { useEffect, useMemo, useState, type ReactNode } from 'react'

import {
  detectInitialLocale,
  STORAGE_KEY,
  translate,
  type AppLocale,
} from '.'
import { localeContext, type LocaleContextValue } from './LocaleContext'

const LocaleContext = localeContext

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<AppLocale>(() => detectInitialLocale())

  useEffect(() => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(STORAGE_KEY, locale)
  }, [locale])

  const value = useMemo<LocaleContextValue>(() => ({
    locale,
    isZh: locale === 'zh-CN',
    setLocale,
    toggleLocale: () => setLocale((current) => (current === 'zh-CN' ? 'en' : 'zh-CN')),
    t: (key, params) => translate(locale, key, params),
  }), [locale])

  return (
    <LocaleContext.Provider value={value}>
      {children}
    </LocaleContext.Provider>
  )
}
