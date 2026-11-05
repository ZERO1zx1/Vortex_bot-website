import { useCallback, useEffect, useState } from 'react'
import { readStored, writeStored } from '../lib/hooks.js'

const KEY = 'aether_js_errors'
const MAX = 50

function load () {
  try {
    return JSON.parse(readStored(KEY, '[]')) || []
  } catch {
    return []
  }
}

/**
 * Captures uncaught runtime errors into localStorage and exposes them behind
 * a footer badge, so a blank or broken section is debuggable without devtools.
 */
export function useErrorLog () {
  const [errors, setErrors] = useState(load)

  const push = useCallback(entry => {
    const next = [...load(), { t: Date.now(), ...entry }].slice(-MAX)
    writeStored(KEY, JSON.stringify(next))
    setErrors(next)
  }, [])

  useEffect(() => {
    const onError = e =>
      push({
        type: 'error',
        msg: e.message || 'Unknown runtime error',
        src: e.filename || '',
        line: e.lineno || 0
      })
    const onRejection = e =>
      push({
        type: 'promise',
        msg: e.reason?.message || String(e.reason),
        src: '',
        line: 0
      })

    window.addEventListener('error', onError)
    window.addEventListener('unhandledrejection', onRejection)
    return () => {
      window.removeEventListener('error', onError)
      window.removeEventListener('unhandledrejection', onRejection)
    }
  }, [push])

  const clear = useCallback(() => {
    try {
      localStorage.removeItem(KEY)
    } catch {
      /* private mode */
    }
    setErrors([])
  }, [])

  return { errors, clear }
}
