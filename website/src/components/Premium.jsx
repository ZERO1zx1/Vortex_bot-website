import { useCallback, useRef } from 'react'
import { useLang } from '../hooks/useLang.jsx'
import { useTilt } from '../hooks/useMotion.js'
import { Icon, SectionHead } from './primitives.jsx'

const PLANS = [
  {
    key: 'free',
    badge: 'FREE',
    badgeClass: '',
    titleKey: 'premium.free',
    price: '₮0',
    features: ['f1', 'f2', 'f3', 'f4', 'f5', 'f6'],
    mutedFrom: 5,
    comingSoon: false,
    ctaKey: 'premium.cta_free',
    featured: false
  },
  {
    key: 'premium',
    badge: '⭐ PREMIUM',
    badgeClass: 'gold',
    icon: 'premium',
    title: 'Premium',
    price: '₮5,000',
    features: ['p1', 'p2', 'p3', 'p4', 'p5', 'p6'],
    comingSoon: true,
    ctaKey: 'premium.cta_premium',
    featured: true
  },
  {
    key: 'server',
    badge: '🏢 SERVER',
    badgeClass: 'cyan',
    titleKey: 'premium.server',
    price: '₮15,000',
    features: ['q1', 'q2', 'q3', 'q4', 'q5', 'q6'],
    comingSoon: true,
    ctaKey: 'premium.cta_server',
    featured: false
  }
]

export function Premium ({ inviteUrl }) {
  const { t } = useLang()

  return (
    <section className='premium' id='premium'>
      <SectionHead
        tag='PREMIUM'
        title={t('premium.title1')}
        accent={t('premium.title2')}
      >
        <span className='coming-soon-pill'>
          🚧 <span>{t('premium.soon')}</span>
        </span>
      </SectionHead>

      <div className='price-grid'>
        {PLANS.map(plan => (
          <PriceCard key={plan.key} plan={plan} inviteUrl={inviteUrl} />
        ))}
      </div>

      <p className='premium-note'>
        <RichPremiumNote text={t('premium.note')} />
      </p>
    </section>
  )
}

function RichPremiumNote ({ text }) {
  // `premium.note` carries a <strong> around ҮНЭГҮЙ / FREE.
  const parts = text.split(/(<strong>.*?<\/strong>)/g)
  return parts.map((part, i) =>
    /^<strong>/.test(part) ? (
      <strong key={i}>{part.replace(/<\/?strong>/g, '')}</strong>
    ) : (
      part
    )
  )
}

function PriceCard ({ plan, inviteUrl }) {
  const { t } = useLang()
  const tilt = useTilt()
  const ref = useRef(null)

  // Plans that are not yet purchasable ignore the click entirely.
  const onClick = useCallback(
    e => {
      if (plan.comingSoon) e.preventDefault()
    },
    [plan.comingSoon]
  )

  const isDisabled = plan.comingSoon

  return (
    <div
      className={`price-card${plan.featured ? ' featured' : ''}`}
      {...tilt}
      ref={ref}
    >
      {plan.icon ? <Icon name={plan.icon} className='pc-icon' /> : null}
      <div className={`pc-badge ${plan.badgeClass}`}>{plan.badge}</div>
      <h3>{plan.titleKey ? t(plan.titleKey) : plan.title}</h3>
      <div className={`pc-price ${plan.badgeClass}`}>
        {plan.price}
        <span>{t('premium.perMonth')}</span>
      </div>

      <ul>
        {plan.features.map((key, i) => {
          const muted = plan.mutedFrom !== undefined && i >= plan.mutedFrom
          return (
            <li key={key} className={muted ? 'muted' : ''}>
              {muted ? '❌' : '✅'} {t(`premium.${key}`)}
            </li>
          )
        })}
      </ul>

      {plan.comingSoon ? (
        <div className='coming-soon-overlay'>{t('premium.coming')}</div>
      ) : null}

      <a
        href={isDisabled ? '#premium' : inviteUrl}
        className={`btn ${plan.featured ? 'btn-primary' : 'btn-ghost'}${
          isDisabled ? ' disabled' : ''
        }`}
        onClick={onClick}
        aria-disabled={isDisabled || undefined}
        {...(isDisabled ? {} : { target: '_blank', rel: 'noopener' })}
      >
        {t(plan.ctaKey)}
      </a>
    </div>
  )
}
