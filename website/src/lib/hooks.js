import { useEffect, useState, useSyncExternalStore } from 'react'

/** Persist to localStorage without throwing in private-mode / quota-exceeded. */
export function readStored (key, fallback = null) {
  try {
    const value = localStorage.getItem(key)
    return value === null ? fallback : value
  } catch {
    return fallback
  }
}

export function writeStored (key, value) {
  try {
    localStorage.setItem(key, value)
  } catch {
    /* quota or private mode — the preference simply does not persist */
  }
}

/** Matches a media query, staying in sync when the user changes it. */
export function useMediaQuery (query) {
  return useSyncExternalStore(
    onChange => {
      const mql = window.matchMedia(query)
      mql.addEventListener('change', onChange)
      return () => mql.removeEventListener('change', onChange)
    },
    () => window.matchMedia(query).matches,
    () => false
  )
}

/** Live rAF-throttled window scroll position. */
export function useScrollY () {
  return useSyncExternalStore(
    onChange => {
      let ticking = false
      const onScroll = () => {
        if (ticking) return
        ticking = true
        requestAnimationFrame(() => {
          ticking = false
          onChange()
        })
      }
      window.addEventListener('scroll', onScroll, { passive: true })
      return () => window.removeEventListener('scroll', onScroll)
    },
    () => window.scrollY,
    () => 0
  )
}

/**
 * Debounce a rapidly-changing value. Keeps the 187-card command list from
 * re-rendering on every keystroke.
 */
export function useDebouncedValue (value, delay = 80) {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(t)
  }, [value, delay])
  return debounced
}

/** True once the element has scrolled into view; used for reveal animations. */
export function useInView (options = {}) {
  const [node, setNode] = useState(null)
  useEffect(() => {
    if (!node) return undefined
    const io = new IntersectionObserver(
      entries => {
        options.onEnter?.(entries[0], io)
      },
      {
        threshold: options.threshold ?? 0.15,
        rootMargin: options.rootMargin ?? '0px 0px -4% 0px'
      }
    )
    io.observe(node)
    return () => io.disconnect()
  }, [node, options.threshold, options.rootMargin]) // eslint-disable-line react-hooks/exhaustive-deps
  return [setNode, node]
}
