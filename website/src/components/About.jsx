import { useLang } from '../hooks/useLang.jsx'
import { useTilt } from '../hooks/useMotion.js'
import { Reveal, RichText, SectionHead } from './primitives.jsx'

const CARDS = [
  { titleKey: 'about.backend', descKey: 'about.backend_d' },
  { titleKey: 'about.framework', descKey: 'about.framework_d' },
  { titleKey: 'about.quality', descKey: 'about.quality_d' }
]

export function About () {
  const { t } = useLang()

  return (
    <section className='about' id='about'>
      <SectionHead
        tag={t('about.tag')}
        title={t('about.title')}
        accent={t('about.title2')}
      />

      <div className='about-layout'>
        <Reveal className='about-text'>
          <h3>
            <RichText text={t('about.q')} />
          </h3>
          <p>
            <RichText text={t('about.p1')} />
          </p>
          <p>
            <RichText text={t('about.p2')} />
          </p>

          <div className='about-stats'>
            <div className='as-item'>
              <span className='as-num'>100%</span>
              <span className='as-label'>{t('about.stat_ui')}</span>
            </div>
            <div className='as-item'>
              <span className='as-num'>LIVE</span>
              <span className='as-label'>Heartbeat</span>
            </div>
            <div className='as-item'>
              <span className='as-num'>11/11</span>
              <span className='as-label'>{t('about.stat_system')}</span>
            </div>
          </div>
        </Reveal>

        <div className='about-cards'>
          {CARDS.map(card => (
            <AboutCard key={card.titleKey} card={card} />
          ))}
        </div>
      </div>
    </section>
  )
}

function AboutCard ({ card }) {
  const { t } = useLang()
  const tilt = useTilt()
  return (
    <div className='about-card' {...tilt}>
      <div className='ac-orb' />
      <h4>
        <RichText text={t(card.titleKey)} />
      </h4>
      <p>
        <RichText text={t(card.descKey)} />
      </p>
    </div>
  )
}
