import { useCallback, useEffect, useRef, useState } from 'react'
import { CONFIG } from '../data/config.js'
import { useLang } from './useLang.jsx'

const ONLINE = 'online'
const OFFLINE = 'offline'

/**
 * Reads the bot's real Online/Offline state.
 *
 * Prefers an external status API when one is configured, then falls back to
 * reading the public `bot_status` row straight from Supabase with the
 * publishable (anon) key. On failure the bot is reported offline rather than
 * optimistically online.
 */
export function useHeartbeat () {
  const [state, setState] = useState({
    status: OFFLINE,
    row: null,
    loading: true
  })
  const { t } = useLang()
  const tRef = useRef(t)
  tRef.current = t

  const check = useCallback(async signal => {
    const apiBase = (CONFIG.API_BASE_URL || '').replace(/\/+$/, '')

    if (apiBase) {
      const row = await viaBackend(apiBase, signal)
      if (row) {
        setState({ status: row.online ? ONLINE : OFFLINE, row, loading: false })
        return
      }
    }

    const row = await viaSupabase(signal)
    if (row) {
      setState({ status: row.online ? ONLINE : OFFLINE, row, loading: false })
      return
    }

    setState({ status: OFFLINE, row: null, loading: false })
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    check(controller.signal)
    const id = setInterval(
      () => check(controller.signal),
      CONFIG.HEARTBEAT_POLL_MS
    )
    return () => {
      controller.abort()
      clearInterval(id)
    }
  }, [check])

  useEffect(() => {
    document.body.classList.toggle('offline-bot', state.status === OFFLINE)
  }, [state.status])

  return state
}

async function fetchWithTimeout (url, options, signal) {
  const ctrl = new AbortController()
  const onAbort = () => ctrl.abort()
  signal?.addEventListener('abort', onAbort)
  const timer = setTimeout(() => ctrl.abort(), CONFIG.STATUS_TIMEOUT_MS)
  try {
    return await fetch(url, {
      ...options,
      signal: ctrl.signal,
      cache: 'no-store'
    })
  } finally {
    clearTimeout(timer)
    signal?.removeEventListener('abort', onAbort)
  }
}

async function viaBackend (apiBase, signal) {
  try {
    const res = await fetchWithTimeout(`${apiBase}/api/status`, {}, signal)
    if (!res.ok) return null
    const data = await res.json()
    if (!data?.ok) return null
    return {
      online: Boolean(data.online),
      last_ping: data.last_ping ?? null,
      uptime_since:
        data.online && data.uptime_secs
          ? new Date(Date.now() - data.uptime_secs * 1000).toISOString()
          : null
    }
  } catch {
    return null
  }
}

async function viaSupabase (signal) {
  const url = (CONFIG.SUPABASE_URL || '').replace(/\/+$/, '')
  const key = CONFIG.SUPABASE_ANON_KEY
  if (!url || !key) return null

  try {
    const res = await fetchWithTimeout(
      `${url}/rest/v1/bot_status?select=id,status,last_ping,uptime_since&id=eq.1`,
      { headers: { apikey: key, Authorization: `Bearer ${key}` } },
      signal
    )
    if (!res.ok) return null
    const rows = await res.json()
    const row = Array.isArray(rows) ? rows[0] : null
    if (!row?.last_ping) return null

    const ageMs = Date.now() - new Date(row.last_ping).getTime()
    const online =
      Number.isFinite(ageMs) &&
      ageMs <= CONFIG.HEARTBEAT_STALE_MS &&
      row.status === 'online'

    return {
      online,
      last_ping: row.last_ping,
      uptime_since: online ? row.uptime_since : null
    }
  } catch {
    return null
  }
}

/* ---------------------------- date formatting ---------------------------- */

const pad = n => String(n).padStart(2, '0')

export function formatAbsolute (iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getFullYear()}.${pad(d.getMonth() + 1)}.${pad(d.getDate())} ${pad(
    d.getHours()
  )}:${pad(d.getMinutes())}`
}

/** "12 мин өмнө" / "3 hours ago" — driven by the `heartbeat.*` dictionary keys. */
export function formatSince (iso, t) {
  if (!iso) return ''
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000)
  if (mins < 1) return t('heartbeat.now')
  if (mins < 60) return `${mins} ${t('heartbeat.ago')}`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h`
  const days = Math.floor(hrs / 24)
  return `${days}d`
}

/** Long-form "last seen" duration, e.g. "3 хоног 4 цаг". */
export function formatDuration (iso, t) {
  if (!iso) return ''
  const totalMinutes = Math.max(
    0,
    Math.floor((Date.now() - new Date(iso).getTime()) / 60000)
  )
  if (totalMinutes < 60) return `${totalMinutes}m`
  const hours = Math.floor(totalMinutes / 60)
  if (hours < 24) return `${hours}h ${totalMinutes % 60}m`
  return `${Math.floor(hours / 24)}d ${hours % 24}h`
}
