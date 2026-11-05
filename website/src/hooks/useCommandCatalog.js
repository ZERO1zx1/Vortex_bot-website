import { useCallback, useEffect, useMemo, useState } from 'react'
import { CAT_META, COMMAND_LIST } from '../data/commands.js'
import { useDebouncedValue } from '../lib/hooks.js'

const ALL = 'all'

function safeDecode (value) {
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

/** `#commands?q=work&cat=Economy` -> { q, cat } */
function readHashParams () {
  const hash = window.location.hash || ''
  const qMatch = hash.match(/[?&]q=([^&#]+)/i)
  const catMatch = hash.match(/[?&]cat=([^&#]+)/i)
  return {
    q: qMatch ? safeDecode(qMatch[1]) : '',
    cat: catMatch ? safeDecode(catMatch[1]) : null
  }
}

export const SLASH_COUNT = COMMAND_LIST.filter(c => c.type === 'slash').length
export const TOTAL_COUNT = COMMAND_LIST.length
export const TEXT_COUNT = TOTAL_COUNT - SLASH_COUNT

/**
 * Search + category filter over the generated catalog, mirrored into the URL
 * so a filtered view can be shared as a link.
 */
export function useCommandCatalog () {
  const initial = useMemo(readHashParams, [])
  const [query, setQuery] = useState(initial.q)
  const [category, setCategory] = useState(
    initial.cat && CAT_META[initial.cat] ? initial.cat : ALL
  )

  const debouncedQuery = useDebouncedValue(query, 80)

  // Keep the component in sync when the hash changes (back button, shared
  // link, hero CTA links).
  useEffect(() => {
    const onHashChange = () => {
      const { q, cat } = readHashParams()
      if (q) setQuery(q)
      if (cat && CAT_META[cat]) setCategory(cat)
    }
    window.addEventListener('hashchange', onHashChange)
    // Deep links can land before this effect runs on a slow first paint.
    const timers = [400, 1200, 3000].map(t => setTimeout(onHashChange, t))
    return () => {
      window.removeEventListener('hashchange', onHashChange)
      timers.forEach(clearTimeout)
    }
  }, [])

  // Reflect state back into the URL.
  useEffect(() => {
    const url = new URL(window.location.href)
    const parts = []
    const trimmed = debouncedQuery.trim()
    if (trimmed) parts.push(`q=${encodeURIComponent(trimmed)}`)
    if (category !== ALL) parts.push(`cat=${encodeURIComponent(category)}`)
    url.hash = parts.length ? `#commands?${parts.join('&')}` : '#commands'
    window.history.replaceState(null, '', url.toString())
  }, [debouncedQuery, category])

  const results = useMemo(() => {
    const q = debouncedQuery.trim().toLowerCase()
    return COMMAND_LIST.filter(c => {
      const catOk = category === ALL || c.cat === category
      if (!catOk) return false
      if (!q) return true
      return (
        c.name.toLowerCase().includes(q) ||
        c.desc.toLowerCase().includes(q) ||
        (c.descEN || '').toLowerCase().includes(q)
      )
    })
  }, [debouncedQuery, category])

  /** Search matches render as a flat grid; category view groups by category. */
  const groups = useMemo(() => {
    const q = debouncedQuery.trim()
    if (q) {
      return results.length ? [{ category: null, commands: results }] : []
    }
    const visible =
      category === ALL
        ? Object.keys(CAT_META).filter(c => c !== ALL)
        : [category]
    return visible
      .map(cat => ({
        category: cat,
        commands: results.filter(c => c.cat === cat)
      }))
      .filter(g => g.commands.length > 0)
  }, [results, debouncedQuery, category])

  const clear = useCallback(() => {
    setQuery('')
    setCategory(ALL)
  }, [])

  return {
    query,
    setQuery,
    category,
    setCategory,
    groups,
    resultCount: results.length,
    isSearching: debouncedQuery.trim().length > 0,
    isEmpty: results.length === 0,
    clear
  }
}

/** Category display label, honouring the active language. */
export function categoryLabel (cat, isEnglish) {
  const meta = CAT_META[cat]
  if (!meta) return cat
  return (isEnglish && meta.labelEN) || meta.label
}
