import { useCallback, useEffect, useRef } from 'react'
import { useLang } from '../hooks/useLang.jsx'
import { useParallax } from '../hooks/useMotion.js'
import { Icon } from './primitives.jsx'
import { TOTAL_COUNT } from '../hooks/useCommandCatalog.js'

const FLOAT_CARDS = [
  { icon: 'economy', label: 'Economy', cls: 'c1' },
  { icon: 'marriage', label: 'Marriage', cls: 'c2' },
  { icon: 'casino', label: 'Casino', cls: 'c3' },
  { icon: 'moderation', label: 'Moderation', cls: 'c4' }
]

export function Hero ({ inviteUrl }) {
  const { lang, t } = useLang()
  const contentRef = useParallax(0.4)
  const visualRef = useParallax(0.8)

  const orbTilt = useRef(null)
  const heroRef = useRef(null)
  const floatCardsRef = useRef([])

  const canHover =
    typeof window !== 'undefined' &&
    window.matchMedia?.('(hover: hover)')?.matches &&
    !window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches

  const onMouseMove = useCallback(e => {
    const hero = heroRef.current
    if (!hero) return
    const r = hero.getBoundingClientRect()
    const tx = ((e.clientX - r.left) / r.width - 0.5) * 2
    const ty = ((e.clientY - r.top) / r.height - 0.5) * 2

    const tilt = orbTilt.current
    if (tilt)
      tilt.style.transform = `rotateX(${(-ty * 9).toFixed(2)}deg) rotateY(${(
        tx * 12
      ).toFixed(2)}deg)`

    floatCardsRef.current.forEach((card, i) => {
      if (!card) return
      // Stagger the depth per card so they drift at different rates.
      const depth = 0.35 + i * 0.16
      card.style.setProperty('--fx', (tx * depth).toFixed(3))
      card.style.setProperty('--fy', (ty * depth).toFixed(3))
    })
  }, [])

  const onMouseLeave = useCallback(() => {
    const tilt = orbTilt.current
    if (tilt) tilt.style.transform = ''
    floatCardsRef.current.forEach(card => {
      if (!card) return
      card.style.removeProperty('--fx')
      card.style.removeProperty('--fy')
    })
  }, [])

  // Reset the orbit tilt if the viewport changes while the pointer is away.
  useEffect(() => {
    window.addEventListener('blur', onMouseLeave)
    return () => window.removeEventListener('blur', onMouseLeave)
  }, [onMouseLeave])

  return (
    <section
      className='hero'
      id='home'
      ref={heroRef}
      onMouseMove={canHover ? onMouseMove : undefined}
      onMouseLeave={canHover ? onMouseLeave : undefined}
    >
      <div className='hero-content' ref={contentRef}>
        <div className='hero-kicker'>
          <span>PROJECT AETHER</span>
          <span>蒼穹 // 03</span>
        </div>
        <div className='hero-badge'>
          {lang === 'en'
            ? '✦ Mongolian Discord community system'
            : '✦ Монгол Discord community system'}
        </div>
        <h1 className='hero-title'>
          <span className='title-orbitron'>𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹</span>
        </h1>
        <div className='hero-jp' aria-hidden='true'>
          蒼穹を越えて
        </div>
        <p className='hero-subtitle'>
          {lang === 'en' ? (
            <>
              Run your server&apos;s whole life from economy to ticket
              automation with one <strong>anime-tech Discord ecosystem.</strong>
            </>
          ) : (
            <>
              Economy-оос ticket automation хүртэлх серверийн бүх амьдралыг нэг
              дор удирдах <strong>anime-tech Discord ecosystem.</strong>
            </>
          )}
        </p>

        <div className='hero-actions'>
          <a
            href={inviteUrl}
            className='btn btn-primary'
            target='_blank'
            rel='noopener'
          >
            <span className='btn-icon'>⚡</span>
            {lang === 'en' ? 'Join the server' : 'Server-т элсэх'}
          </a>
          <a href='#commands' className='btn btn-ghost'>
            <span className='btn-icon'>📜</span>
            <span>{t('hero.viewCommands')}</span>
          </a>
        </div>

        <div className='hero-tags'>
          <span>
            <b>11</b> {lang === 'en' ? 'core systems' : 'үндсэн систем'}
          </span>
          <span>
            <b>{TOTAL_COUNT}</b>{' '}
            {lang === 'en' ? 'active commands' : 'active command'}
          </span>
          <span>
            <i /> SYSTEM ONLINE
          </span>
        </div>
      </div>

      <div className='hero-visual' ref={visualRef}>
        <div className='orb-tilt' id='orb-tilt' ref={orbTilt}>
          <div className='orb-scene'>
            <div className='orb' id='hero-orb'>
              <div className='orb-glow' />
              <div className='orb-ring ring-1' />
              <div className='orb-ring ring-2' />
              <div className='orb-ring ring-3' />
              <div className='orb-face'>蒼</div>
            </div>
            <div className='orb-shadow' />
          </div>
        </div>

        {FLOAT_CARDS.map((card, i) => (
          <div
            key={card.cls}
            className={`float-card ${card.cls}`}
            data-tilt
            ref={el => {
              floatCardsRef.current[i] = el
            }}
          >
            <Icon name={card.icon} className='fc-icon-svg' /> {card.label}
          </div>
        ))}
      </div>
    </section>
  )
}
