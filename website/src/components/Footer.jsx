import { useState } from 'react'
import { useLang } from '../hooks/useLang.jsx'
import { useErrorLog } from '../hooks/useErrorLog.js'

const FOOTER_LINKS = [
  { href: '#features', key: 'nav.features' },
  { href: '#commands', key: 'nav.commands' },
  { href: '#stats', key: 'nav.stats' },
  { href: '#community', label: 'Community' },
  { href: '#premium', label: 'Premium' },
  { href: '#changelog', key: 'nav.changelog' },
  { href: '#faq', key: 'footer.faq' }
]

export function Footer () {
  const { t, isEnglish } = useLang()
  const { errors, clear } = useErrorLog()
  const [logOpen, setLogOpen] = useState(false)

  return (
    <footer className='footer'>
      <div className='footer-brand'>
        𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹 <span>•</span> <span>{t('footer.brand')}</span>
      </div>

      <div className='footer-links'>
        {FOOTER_LINKS.map(link => (
          <a key={link.href} href={link.href}>
            {link.key ? t(link.key) : link.label}
          </a>
        ))}

        {errors.length > 0 ? (
          <button
            id='err-badge'
            type='button'
            className='show'
            onClick={() => setLogOpen(true)}
            aria-label={isEnglish ? 'Site errors' : 'Сайтын алдаа'}
          >
            ⚠ {errors.length}
          </button>
        ) : null}
      </div>

      <div className='footer-copy'>
        <span>{t('footer.copy')}</span>
      </div>

      {logOpen ? (
        <ErrorModal
          errors={errors}
          onClose={() => setLogOpen(false)}
          onClear={clear}
        />
      ) : null}
    </footer>
  )
}

function ErrorModal ({ errors, onClose, onClear }) {
  return (
    <div className='err-modal open' id='err-modal'>
      <div className='err-modal-backdrop' onClick={onClose} />
      <div
        className='err-modal-box'
        role='dialog'
        aria-modal='true'
        aria-label='Site error log'
      >
        <div className='err-modal-head'>
          <span>🛠 Site error log</span>
          <button
            type='button'
            className='err-modal-close'
            onClick={onClose}
            aria-label='Close'
          >
            ✕
          </button>
        </div>
        <div className='err-modal-body'>
          {errors.length === 0 ? (
            <div className='err-empty'>✅ No errors recorded.</div>
          ) : (
            [...errors].reverse().map(e => (
              <div className='err-entry' key={`${e.t}-${e.msg}`}>
                <span className='err-type'>
                  {e.type === 'promise' ? 'PROMISE' : 'ERR'}
                </span>
                <span className='err-time'>
                  {new Date(e.t).toLocaleString()}
                </span>
                <span className='err-msg'>{e.msg}</span>
                {e.src ? (
                  <span className='err-src'>
                    {e.src}:{e.line}
                  </span>
                ) : null}
              </div>
            ))
          )}
        </div>
        <div className='err-modal-foot'>
          <button type='button' className='err-clear-btn' onClick={onClear}>
            🧹 Clear log
          </button>
        </div>
      </div>
    </div>
  )
}
