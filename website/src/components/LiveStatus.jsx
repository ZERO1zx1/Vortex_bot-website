import { useRef } from 'react'
import { useLang } from '../hooks/useLang.jsx'
import {
  useHeartbeat,
  formatAbsolute,
  formatDuration,
  formatSince
} from '../hooks/useHeartbeat.js'
import { useStatusGraph } from '../hooks/useStatusGraph.js'
import { useTilt } from '../hooks/useMotion.js'
import { SectionHead } from './primitives.jsx'

const RUNTIME = [
  { icon: '🐍', value: 'Python 3.12', key: 'status.runtime' },
  { icon: '🤖', value: 'discord.py 2.6', key: 'status.framework' },
  { icon: '⚡', value: 'Supabase', key: 'status.database' },
  { icon: '🛰️', value: '24/7', key: 'status.uptime_goal' }
]

export function LiveStatus () {
  const { t, isEnglish } = useLang()
  const { status, row, loading } = useHeartbeat()
  const isOnline = status === 'online'
  const tilt = useTilt()
  const graphRef = useRef(null)

  useStatusGraph(graphRef, isOnline)

  let lastSeenText = t('heartbeat.checking')
  if (!loading) {
    if (isOnline) {
      const uptime = row?.uptime_since
        ? `Uptime: ${formatDuration(row.uptime_since, t)}`
        : 'Uptime …'
      const heartbeat = row?.last_ping
        ? `Heartbeat: ${formatSince(row.last_ping, t)}`
        : t('heartbeat.now')
      lastSeenText = `${uptime} · ${heartbeat}`
    } else if (row?.last_ping) {
      lastSeenText = isEnglish
        ? `Last online ${formatSince(row.last_ping, t)} (${formatAbsolute(
            row.last_ping
          )})`
        : `Сүүлд онлайн байсан: ${formatSince(
            row.last_ping,
            t
          )} (${formatAbsolute(row.last_ping)})`
    } else {
      lastSeenText = isEnglish
        ? 'The bot is currently offline.'
        : 'Бот одоогоор унтарсан байна'
    }
  }

  return (
    <section className='live-status' id='livestatus'>
      <SectionHead
        tag={t('status.tag')}
        title={t('status.title1')}
        accent={t('status.title2')}
      />

      <div className='status-card' {...tilt}>
        <div className='sc-glow' />

        <div className='status-row'>
          <div className='status-orb'>
            <div
              className={`status-dot ${isOnline ? 'online' : 'offline'}`}
              id='status-dot'
            />
            <div className='so-ring' />
          </div>

          <div className='status-main'>
            <div className='status-title'>
              {t('status.title_prefix')}{' '}
              <span className='online-text' id='online-text'>
                {isOnline ? 'Online' : 'Offline'}
              </span>
            </div>
            <div className='status-sub'>{t('status.sub')}</div>
            <div className='status-uptime' id='last-seen' aria-live='polite'>
              {lastSeenText}
            </div>
          </div>

          <div className='status-badge'>v1.0</div>
        </div>

        <div className='status-grid'>
          {RUNTIME.map(item => (
            <div className='sg-item' key={item.key} data-reveal>
              <span className='sg-icon' aria-hidden='true'>
                {item.icon}
              </span>
              <div className='sg-num'>{item.value}</div>
              <div className='sg-label'>{t(item.key)}</div>
            </div>
          ))}
        </div>

        <canvas
          id='status-graph'
          className='status-graph'
          ref={graphRef}
          aria-hidden='true'
        />

        <div className='status-refresh'>
          {isEnglish ? (
            <>
              See the bot&apos;s detailed status in Discord with the{' '}
              <code>/status</code> command.
            </>
          ) : (
            <>
              Ботын нарийвчилсан status-ийг Discord дээр <code>/status</code>{' '}
              командаар харна уу.
            </>
          )}
        </div>
      </div>
    </section>
  )
}
