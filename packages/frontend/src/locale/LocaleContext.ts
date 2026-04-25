import { createContext, useContext } from 'react'

import { translate, type AppLocale, type MessageParams } from '.'

export interface LocaleContextValue {
  locale: AppLocale
  isZh: boolean
  setLocale: (locale: AppLocale) => void
  toggleLocale: () => void
  t: (key: string, params?: MessageParams) => string
}

const defaultLocale: LocaleContextValue = {
  locale: 'en',
  isZh: false,
  setLocale: () => {},
  toggleLocale: () => {},
  t: (key, params) => translate('en', key, params),
}

export const localeContext = createContext<LocaleContextValue>(defaultLocale)

export function useLocale() {
  return useContext(localeContext)
}
