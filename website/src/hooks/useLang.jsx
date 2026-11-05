import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from 'react'
import { DICTIONARY, LANGS, translate } from '../i18n/dictionary.js'
import { readStored, writeStored } from '../lib/hooks.js'

/**
 * Language state.
 *
 * The pre-React site shipped a complete MN/EN dictionary but no switcher UI,
 * so `applyLang('mn')` ran unconditionally and the English copy was unreachable
 * dead weight. The switcher now exists in the navbar and the choice persists.
 */
const LangContext = createContext(null)

const STORAGE_KEY = 'aether-lang'
const DEFAULT_LANG = 'mn'

function readInitialLang () {
  const saved = readStored(STORAGE_KEY)
  return LANGS.some(l => l.code === saved) ? saved : DEFAULT_LANG
}

export function LangProvider ({ children }) {
  const [lang, setLang] = useState(readInitialLang)
  const dict = DICTIONARY[lang] ?? DICTIONARY[DEFAULT_LANG]

  useEffect(() => {
    document.documentElement.lang = lang
    writeStored(STORAGE_KEY, lang)
  }, [lang])

  const t = useCallback(key => translate(dict, key), [dict])

  const value = useMemo(
    () => ({
      lang,
      dict,
      t,
      langs: LANGS,
      isEnglish: lang === 'en',
      setLang
    }),
    [lang, dict, t]
  )

  return <LangContext.Provider value={value}>{children}</LangContext.Provider>
}

export function useLang () {
  const ctx = useContext(LangContext)
  if (!ctx) throw new Error('useLang must be used inside <LangProvider>')
  return ctx
}
