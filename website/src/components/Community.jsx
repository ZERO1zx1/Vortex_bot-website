import { useLang } from '../hooks/useLang.jsx'
import { Reveal, RichText } from './primitives.jsx'

const INTRO_CARDS = [
  { icon: '🎮', titleKey: 'community.gaming', descKey: 'community.gaming_d' },
  { icon: '💎', titleKey: 'community.topup', descKey: 'community.topup_d' },
  { icon: '🎁', titleKey: 'community.event', descKey: 'community.event_d' },
  { icon: '👥', titleKey: 'community.active', descKey: 'community.active_d' }
]

const RULES = [
  ['r1t', 'r1'],
  ['r2t', 'r2'],
  ['r3t', 'r3'],
  ['r4t', 'r4'],
  ['r5t', 'r5'],
  ['r6t', 'r6'],
  ['r7t', 'r7'],
  ['r8t', 'r8']
]

const PUNISH_STEPS = [
  ['01 WARN', '⚠️ Warning'],
  ['02 WARN', '🔇 2h Mute'],
  ['04 WARN', '🔇 6h Mute'],
  ['06 WARN', '🔇 9h Mute'],
  ['08 WARN', '🔇 12h Mute'],
  ['10 WARN', '🔇 24h Mute'],
  ['12 WARN', '🔨 Permanent Ban']
]

const STAFF = [
  {
    name: 'Vortex | 虚空',
    handle: 'vortex_1269',
    role: 'FOUNDER / OWNER',
    roleClass: 'role-founder',
    userId: '1269304623135457281',
    bioKey: 'vortex',
    avatar: 'vortex.png'
  },
  {
    name: 'Irla',
    handle: 'irlabug',
    role: 'CO-OWNER',
    roleClass: 'role-coowner',
    userId: '1294315450355941471',
    bioKey: 'irla',
    avatar: 'irla.png'
  },
  {
    name: 'Aferrz',
    handle: 'aferrz',
    role: 'CO-OWNER',
    roleClass: 'role-coowner',
    userId: '1264431949351485583',
    bioKey: 'aferrz',
    avatar: 'aferrz.png'
  },
  {
    name: 'Aiku',
    handle: 'aaayq_',
    role: 'ADMIN',
    roleClass: 'role-admin',
    userId: '1303208774487511100',
    bioKey: 'aiku',
    avatar: 'aiku.png'
  },
  {
    name: 'Bakuna',
    handle: 'eggland_09653',
    role: 'MODERATOR',
    roleClass: 'role-mod',
    userId: '1389059584919863357',
    bioKey: 'bakuna',
    avatar: 'bakuna.png'
  },
  {
    name: 'Aiken',
    handle: 'amraabn.',
    role: 'MODERATOR',
    roleClass: 'role-mod',
    userId: '1109125727988748411',
    bioKey: 'aiken',
    avatar: 'aiken.png'
  }
]

export function Community () {
  const { t, isEnglish } = useLang()

  return (
    <section className='community' id='community'>
      <Reveal className='section-head'>
        <span className='eyebrow'>{t('community.tag')}</span>
        <h2 className='section-title'>
          {isEnglish ? (
            <>
              Official <span className='accent'>AETHER</span> server
            </>
          ) : (
            <>
              Албан ёсны <span className='accent'>AETHER</span> сервер
            </>
          )}
        </h2>
        <p className='section-sub'>
          <RichText text={t('community.subtitle')} />
        </p>
      </Reveal>

      <Reveal className='community-logo-wrap'>
        <img
          src='/assets/aether_logo.png'
          alt='AETHER logo'
          className='community-logo'
          loading='lazy'
        />
        <span className='community-logo-fallback'>蒼穹</span>
      </Reveal>

      <Reveal className='community-intro'>
        <p>
          <RichText text={t('community.intro')} />
        </p>
        <div className='intro-grid'>
          {INTRO_CARDS.map(card => (
            <div className='intro-card' key={card.titleKey}>
              <span className='intro-icon' aria-hidden='true'>
                {card.icon}
              </span>
              <h4>
                <RichText text={t(card.titleKey)} />
              </h4>
              <p>
                <RichText text={t(card.descKey)} />
              </p>
            </div>
          ))}
        </div>
        <p className='community-slogan'>
          <strong>
            {isEnglish
              ? 'AETHER — PLAY. CONNECT. WIN.'
              : 'AETHER — PLAY. CONNECT. WIN.'}
          </strong>{' '}
          🌌
        </p>
      </Reveal>

      <Reveal as='h3' className='community-sub'>
        <span className='accent'>𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹</span>{' '}
        <RichText text={t('community.rules')} />
      </Reveal>

      <Reveal className='rules-grid'>
        {RULES.map(([titleKey, bodyKey], i) => (
          <div className='rule-card' key={bodyKey}>
            <span className='rule-num'>{String(i + 1).padStart(2, '0')}</span>
            <h4>
              <RichText text={t(titleKey)} />
            </h4>
            <p>
              <RichText text={t(bodyKey)} />
            </p>
          </div>
        ))}
      </Reveal>

      <Reveal as='h3' className='community-sub'>
        ⚔️ <span className='accent'>{t('community.punish')}</span>
      </Reveal>

      <Reveal className='punish-wrap'>
        <div className='punish-track'>
          {PUNISH_STEPS.map(([warn, action]) => (
            <div
              key={warn}
              className={`punish-step${
                action.includes('Permanent') ? ' punish-ban' : ''
              }`}
            >
              <span className='punish-warn'>{warn}</span>
              <span className='punish-act'>{action}</span>
            </div>
          ))}
        </div>
        <p className='punish-note'>
          <strong>{t('community.punish_imp')}</strong>{' '}
          <RichText text={t('community.punish_note')} />{' '}
          <em>
            {isEnglish
              ? 'Respect the community. Follow the rules. Enjoy 𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹.'
              : 'Дүрмийг дагаж, нийгэмээ хүндэтгэ. 𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹.'}
          </em>
        </p>
      </Reveal>

      <Reveal as='h3' className='community-sub'>
        <RichText text={t('community.staff_title')} />
      </Reveal>

      <Reveal
        className='community-intro'
        style={{ maxWidth: 900, margin: '0 auto 32px', textAlign: 'center' }}
      >
        <p>
          <RichText text={t('community.staff_intro')} />
        </p>
      </Reveal>

      <Reveal className='staff-grid'>
        {STAFF.map(member => (
          <div className='staff-card' key={member.handle} tabIndex={0}>
            <div className='staff-avatar'>
              <img
                src={`/assets/staff/${member.avatar}`}
                alt={member.name}
                loading='lazy'
              />
            </div>
            <span className={`staff-role ${member.roleClass}`}>
              {member.role}
            </span>
            <h4>{member.name}</h4>
            <span className='staff-uname'>discord: @{member.handle}</span>
            <div className='staff-desc'>
              <p>
                <RichText text={t(`staff.bio.${member.bioKey}`)} />
              </p>
              <a
                className='staff-profile'
                href={`https://discord.com/users/${member.userId}`}
                target='_blank'
                rel='noopener'
              >
                {isEnglish ? '🔗 Discord profile' : '🔗 Discord профиль'}
              </a>
            </div>
          </div>
        ))}
      </Reveal>
    </section>
  )
}
