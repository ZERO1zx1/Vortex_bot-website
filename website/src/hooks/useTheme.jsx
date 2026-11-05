import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from 'react'
import { readStored, writeStored } from '../lib/hooks.js'

/**
 * Theme is applied as `data-theme` on <html> so the existing CSS custom
 * properties keep working, and mirrored into the meta theme-color tag.
 */
const ThemeContext = createContext(null)

const STORAGE_KEY = 'aether-theme'

function readInitialTheme () {
  const saved = readStored(STORAGE_KEY)
  if (saved === 'light' || saved === 'dark') return saved
  if (
    typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-color-scheme: light)').matches
  ) {
    return 'light'
  }
  return 'dark'
}

export function ThemeProvider ({ children }) {
  const [theme, setTheme] = useState(readInitialTheme)
  const isLight = theme === 'light'

  useEffect(() => {
    const root = document.documentElement
    root.setAttribute('data-theme', isLight ? 'light' : 'dark')

    const meta = document.querySelector('meta[name="theme-color"]')
    if (meta) meta.setAttribute('content', isLight ? '#F7F9FC' : '#0B0B14')

    writeStored(STORAGE_KEY, theme)
  }, [theme, isLight])

  const toggle = useCallback(
    () => setTheme(t => (t === 'light' ? 'dark' : 'light')),
    []
  )

  const value = useMemo(
    () => ({ theme, isLight, toggle }),
    [theme, isLight, toggle]
  )
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme () {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used inside <ThemeProvider>')
  return ctx
}
