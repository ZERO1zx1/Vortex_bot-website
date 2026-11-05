import { useMemo } from 'react'
import { useLang } from '../hooks/useLang.jsx'
import { useTilt } from '../hooks/useMotion.js'

/** Show the bare invite code (discord.gg/xxxx) rather than the full URL. */
export function inviteDisplay (url) {
  try {
    const parsed = new URL(url)
    return `${parsed.host}${parsed.pathname}`.replace(/\/$/, '')
  } catch {
    return url
  }
}

export function InviteCta ({ inviteUrl }) {
  const { t } = useLang()
  const tilt = useTilt()
  const code = useMemo(() => inviteDisplay(inviteUrl), [inviteUrl])

  return (
    <section className='invite' id='invite'>
      <div className='invite-card' {...tilt}>
        <div className='invite-orb' aria-hidden='true'>
          <div className='invite-orb-glow' />
          🚀
        </div>
        <h2>
          <span>{t('invite.title1')}</span>{' '}
          <span className='accent'>{t('invite.title2')}</span>
        </h2>
        <p>
          <span>{t('invite.sub')}</span>
        </p>
        <a
          href={inviteUrl}
          className='btn btn-primary btn-lg invite-pulse'
          id='invite-btn'
          target='_blank'
          rel='noopener'
        >
          <span className='btn-icon'>🚀</span>
          <span>{t('invite.btn')}</span>
        </a>
        <div className='invite-meta' id='invite-meta'>
          <code>{code}</code>
        </div>
      </div>
    </section>
  )
}
