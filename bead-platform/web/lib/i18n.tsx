'use client'

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react'

// ---------------------------------------------------------------------------
// Supported locales
// ---------------------------------------------------------------------------
export const SUPPORTED_LOCALES = ['en', 'es', 'fr', 'pt'] as const
export type Locale = (typeof SUPPORTED_LOCALES)[number]

export const LOCALE_LABELS: Record<Locale, string> = {
  en: 'English',
  es: 'Español',
  fr: 'Français',
  pt: 'Português',
}

const STORAGE_KEY = 'bead_locale'
const DEFAULT_LOCALE: Locale = 'en'

// ---------------------------------------------------------------------------
// Deep-get helper: resolves "a.b.c" key paths in nested translation objects
// ---------------------------------------------------------------------------
function deepGet(obj: Record<string, unknown>, path: string): string {
  const parts = path.split('.')
  let current: unknown = obj
  for (const part of parts) {
    if (current === null || typeof current !== 'object') return path
    current = (current as Record<string, unknown>)[part]
  }
  return typeof current === 'string' ? current : path
}

// ---------------------------------------------------------------------------
// Context types
// ---------------------------------------------------------------------------
interface I18nContextValue {
  locale: Locale
  setLocale: (locale: Locale) => void
  t: (key: string) => string
  formatNumber: (value: number, options?: Intl.NumberFormatOptions) => string
  formatDate: (value: Date | string, options?: Intl.DateTimeFormatOptions) => string
  formatCurrency: (value: number, currency?: string) => string
}

const I18nContext = createContext<I18nContextValue | null>(null)

// ---------------------------------------------------------------------------
// Detect the best locale from the browser's language preferences
// ---------------------------------------------------------------------------
function detectBrowserLocale(): Locale {
  if (typeof navigator === 'undefined') return DEFAULT_LOCALE
  const langs = navigator.languages ?? [navigator.language]
  for (const lang of langs) {
    const base = lang.split('-')[0] as Locale
    if (SUPPORTED_LOCALES.includes(base)) return base
  }
  return DEFAULT_LOCALE
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------
export function TranslationProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(DEFAULT_LOCALE)
  const [messages, setMessages] = useState<Record<string, unknown>>({})

  // Initialise locale from storage or browser on first render
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY) as Locale | null
    const resolved =
      stored && SUPPORTED_LOCALES.includes(stored) ? stored : detectBrowserLocale()
    setLocaleState(resolved)
  }, [])

  // Load the message file whenever the locale changes
  useEffect(() => {
    import(`../messages/${locale}.json`)
      .then((mod) => setMessages(mod.default ?? mod))
      .catch(() => {
        // Fallback: load English
        import('../messages/en.json').then((mod) =>
          setMessages(mod.default ?? mod)
        )
      })
  }, [locale])

  const setLocale = useCallback((next: Locale) => {
    localStorage.setItem(STORAGE_KEY, next)
    setLocaleState(next)
  }, [])

  /** Translate a dot-notation key, e.g. "dashboard.title" */
  const t = useCallback(
    (key: string): string => deepGet(messages as Record<string, unknown>, key),
    [messages]
  )

  /** Format a number according to the current locale */
  const formatNumber = useCallback(
    (value: number, options?: Intl.NumberFormatOptions): string =>
      new Intl.NumberFormat(locale, options).format(value),
    [locale]
  )

  /** Format a date according to the current locale */
  const formatDate = useCallback(
    (value: Date | string, options?: Intl.DateTimeFormatOptions): string => {
      const date = typeof value === 'string' ? new Date(value) : value
      return new Intl.DateTimeFormat(locale, options).format(date)
    },
    [locale]
  )

  /** Format a currency value according to the current locale */
  const formatCurrency = useCallback(
    (value: number, currency = 'USD'): string =>
      new Intl.NumberFormat(locale, { style: 'currency', currency }).format(value),
    [locale]
  )

  return (
    <I18nContext.Provider
      value={{ locale, setLocale, t, formatNumber, formatDate, formatCurrency }}
    >
      {children}
    </I18nContext.Provider>
  )
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------
export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext)
  if (!ctx) {
    throw new Error('useI18n must be used inside <TranslationProvider>')
  }
  return ctx
}
