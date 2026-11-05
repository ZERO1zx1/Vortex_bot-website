import { useLang } from '../hooks/useLang.jsx'
import { useCountUp, useTilt } from '../hooks/useMotion.js'
import {
  SLASH_COUNT,
  TOTAL_COUNT,
  TEXT_COUNT
} from '../hooks/useCommandCatalog.js'
import { SectionHead } from './primitives.jsx'

/** Animated numeric stat. */
function CountStat ({ icon, value, suffix = '', label, variant }) {
  const tilt = useTilt()
  const counter = useCountUp(value, { suffix })

  return (
    <div className={`stat-card ${variant}`} {...tilt}>
      <div className='stat-icon' aria-hidden='true'>
        {icon}
      </div>
      <div className='stat-num' ref={counter.ref}>
        {counter.text}
      </div>
      <div className='stat-label'>{label}</div>
    </div>
  )
}

/** Static-text stat (e.g. the database engine name). */
function TextStat ({ icon, text, label, variant }) {
  const tilt = useTilt()
  return (
    <div className={`stat-card ${variant}`} {...tilt}>
      <div className='stat-icon' aria-hidden='true'>
        {icon}
      </div>
      <div className='stat-num'>{text}</div>
      <div className='stat-label'>{label}</div>
    </div>
  )
}

export function Stats () {
  const { t } = useLang()

  return (
    <section className='stats' id='stats'>
      <SectionHead
        tag={t('stats.tag')}
        title={t('stats.title1')}
        accent={t('stats.title2')}
      />

      <div className='stat-grid'>
        <CountStat
          icon='🧩'
          value={11}
          variant='cog'
          label={t('stats.systems')}
        />
        <CountStat
          icon='⚡'
          value={TOTAL_COUNT}
          variant='slash'
          label={`${t(
            'stats.cmd'
          )} (${SLASH_COUNT} slash / ${TEXT_COUNT} text)`}
        />
        <TextStat
          icon='🗄️'
          text='SQL'
          variant='db'
          label={t('stats.database')}
        />
        <CountStat
          icon='🕐'
          value={24}
          suffix='/7'
          variant='uptime'
          label={t('stats.uptime')}
        />
      </div>
    </section>
  )
}
