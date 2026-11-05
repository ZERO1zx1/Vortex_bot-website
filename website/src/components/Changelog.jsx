import { useLang } from '../hooks/useLang.jsx'
import { Reveal, RichText, SectionHead } from './primitives.jsx'

const ENTRIES = [
  {
    date: '2026-09-20',
    featured: true,
    pillClass: 'new',
    pillKey: 'changelog.latest',
    title: 'Aether Prism Archive — Web redesign',
    bodyKey: 'cl.v31_d',
    meta: ['DESIGN SYSTEM', 'COMMAND SYNC', 'MOBILE UI']
  },
  {
    date: '2026-08-24',
    pillClass: 'new',
    pillKey: 'cl.new',
    titleKey: 'changelog.v30_t',
    bodyKey: 'changelog.v30_d',
    meta: []
  },
  {
    date: '2026-08-19',
    pillClass: 'new',
    pillKey: 'cl.new',
    titleKey: 'changelog.v29_t',
    bodyKey: 'changelog.v29_d',
    meta: []
  },
  {
    date: '2026-08-18',
    pillClass: 'new',
    pill: 'v2.3',
    titleKey: 'cl.v23_t',
    bodyKey: 'cl.v23_d',
    meta: []
  },
  {
    date: '2026-08-17',
    pillClass: 'fix',
    pillKey: 'cl.fix',
    titleKey: 'cl.v22_t',
    bodyKey: 'cl.v22_d',
    meta: []
  },
  {
    date: '2026-08-15',
    pillClass: 'new',
    pill: 'v2.1',
    titleKey: 'cl.v21_t',
    bodyKey: 'cl.v21_d',
    meta: []
  }
]

export function Changelog () {
  const { t } = useLang()

  return (
    <section className='changelog' id='changelog'>
      <SectionHead
        tag={t('cl.tag')}
        title={t('cl.title1')}
        accent={t('cl.title2')}
      />

      <div className='cl-timeline'>
        {ENTRIES.map(entry => (
          <Reveal
            key={entry.date}
            className={`cl-item${entry.featured ? ' cl-featured' : ''}`}
          >
            <div className='cl-date'>{entry.date}</div>
            <div className='cl-card'>
              <span className={`cl-pill ${entry.pillClass}`}>
                {entry.pillKey ? t(entry.pillKey) : entry.pill}
              </span>
              <h4>{entry.titleKey ? t(entry.titleKey) : entry.title}</h4>
              <p>
                {entry.bodyKey ? (
                  <RichText text={t(entry.bodyKey)} />
                ) : (
                  entry.body
                )}
              </p>
              {entry.meta.length ? (
                <div className='cl-meta'>
                  {entry.meta.map(m => (
                    <span key={m}>{m}</span>
                  ))}
                </div>
              ) : null}
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  )
}
