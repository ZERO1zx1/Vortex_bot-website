import { useLang } from '../hooks/useLang.jsx'
import { useTilt } from '../hooks/useMotion.js'
import { Icon, SectionHead } from './primitives.jsx'

const FEATURES = [
  {
    icon: 'economy',
    orb: 'fc-econ',
    titleKey: 'feat.econ',
    title: 'Эдийн засаг',
    desc: 'Wallet, bank, daily, work, transfer болон бүрэн transaction history.'
  },
  {
    icon: 'leveling',
    orb: 'fc-lvl',
    title: 'Level / Ranking / Profile',
    desc: 'XP, rank card, leaderboard, server activity болон profile статистик.'
  },
  {
    icon: 'marriage',
    orb: 'fc-love',
    titleKey: 'feat.mar',
    title: 'Гэрлэл / Гэр бүл',
    descKey: 'feat.mar_d',
    desc: 'Учрахаас эхлээд гэр бүлийн мод хүртэл. Хайртай хүнтэйгээ гэрлэ.'
  },
  {
    icon: 'shop',
    orb: 'fc-shop',
    title: 'Shop & Inventory',
    desc: 'Item худалдаж авах, ашиглах, equip хийх болон inventory картаар харах.'
  },
  {
    icon: 'casino',
    orb: 'fc-cas',
    titleKey: 'feat.cas',
    title: 'Казино & Тоглоом',
    desc: 'Blackjack, slot, roulette, high-low, crash, trivia болон casual games.'
  },
  {
    icon: 'fun',
    orb: 'fc-maf',
    title: 'Ticket & Giveaway',
    desc: 'Setup-аас бэлэн panel үүсгэж, төрөл сонголт, transcript log, giveaway удирдана.'
  },
  {
    icon: 'moderation',
    orb: 'fc-mod',
    title: 'Moderation & Statistics',
    desc: 'Ban, kick, warn, timeout, automod, staff activity болон server statistics.'
  },
  {
    icon: 'fun',
    orb: 'fc-fun',
    title: 'Automation, Fun & Confessions',
    desc: 'Join/leave webhook automation, anime reactions, meme болон нууц confession.'
  }
]

function FeatureCard ({ feature }) {
  const tilt = useTilt()
  const { t } = useLang()

  return (
    <div className='feature-card' {...tilt}>
      <div className={`fc-orb ${feature.orb}`} />
      <Icon name={feature.icon} className='fc-svg' />
      <h3>{feature.titleKey ? t(feature.titleKey) : feature.title}</h3>
      <p>{feature.descKey ? t(feature.descKey) : feature.desc}</p>
    </div>
  )
}

export function Features () {
  const { t } = useLang()
  return (
    <section className='features' id='features'>
      <SectionHead tag={t('features.tag')}>
        <span>{t('features.title1')} </span>
        <span className='accent'>11 үндсэн систем.</span>
      </SectionHead>

      <div className='feature-grid'>
        {FEATURES.map(feature => (
          <FeatureCard key={feature.title} feature={feature} />
        ))}
      </div>
    </section>
  )
}
