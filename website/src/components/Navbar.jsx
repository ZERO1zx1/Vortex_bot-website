import { useEffect, useState } from 'react'
import { useLang } from '../hooks/useLang.jsx'
import { useTheme } from '../hooks/useTheme.jsx'
import { useScrollY } from '../lib/hooks.js'
/**
 * Primary navigation.
 *
 * Link order mirrors the section order on the page, so following the nav
 * always moves forward: Onchl → Commands → Stats → Community → About →
 * Premium → Changelog → FAQ.
 */
const LINKS = [
  { href: '#features', key: 'nav.features' },
  { href: '#commands', key: 'nav.commands' },
  { href: '#stats', key: 'nav.stats' },
  { href: '#community', label: 'Community' },
  { href: '#about', label: 'About' },
  { href: '#premium', label: 'Premium' },
  { href: '#changelog', key: 'nav.changelog' },
  { href: '#faq', key: 'footer.faq' },
]
/**
 * MN / EN switcher.
 *
 * Rendered twice: once in the navbar bar for wide viewports, and once inside
 * the collapsible menu for phones, where the bar has no room for it. CSS shows
 * exactly one of the two at any given breakpoint.
 */
function LanguageSwitch({ placement }) {
  const { lang, setLang, langs } = useLang()
  return (
    <div
      className={`lang-switch lang-switch-${placement}`}
      role="group"
      aria-label={lang === 'en' ? 'Language' : 'Хэл'}
    >
      {langs.map((l) => (
        <button
          key={l.code}
          type="button"
          className={`lang-btn${lang === l.code ? ' active' : ''}`}
          data-lang={l.code}
          lang={l.htmlLang}
          title={l.label}
          aria-label={l.label}
          aria-pressed={lang === l.code}
          onClick={() => setLang(l.code)}
        >
          {l.short ?? l.label}
        </button>
      ))}
    </div>
  )
}

export function Navbar({ inviteUrl }) {
  const { t, isEnglish } = useLang()
  const { isLight, toggle } = useTheme()
  const scrollY = useScrollY()
  const [open, setOpen] = useState(false)
  // Close the mobile menu on resize so it cannot stay stuck open.
  // Must match the navbar collapse breakpoint in style.css (1200px).
  useEffect(() => {
    const mq = window.matchMedia('(min-width: 1201px)')
    const onChange = () => mq.matches && setOpen(false)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])
  // Close the mobile menu on Escape.
  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])
  const scrolled = scrollY > 40
  const background = isLight
    ? scrolled
      ? 'rgba(247,249,252,0.94)'
      : 'rgba(247,249,252,0.78)'
    : scrolled
      ? 'rgba(11,11,20,0.92)'
      : 'rgba(11,11,20,0.65)'
  return (
    // `nav-open` exists so the stylesheet can drop the navbar's clip-path while the
// menu is open: clip-path clips descendants to the navbar's own box, which
// made the dropdown invisible and untappable on small screens.
<nav className={`navbar${open ? ' nav-open' : ''}`} style={{ background }}>
      <div className="nav-brand">
        <img
          src="/assets/aether_logo.png"
          alt="Aether 蒼穹 logo"
          className="brand-logo-img"
          width="36"
          height="36"
        />
        <div className="brand-orb" />
        <span>𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹</span>
      </div>

      <div className={`nav-links${open ? ' open' : ''}`} id="primary-nav">
        {LINKS.map((link) => (
          <a key={link.href} href={link.href} onClick={() => setOpen(false)}>
            {link.key ? t(link.key) : link.label}
          </a>
        ))}
        <div className="nav-links-footer">
          <LanguageSwitch placement="menu" />
        </div>
      </div>

      <div className="nav-controls">
        <LanguageSwitch placement="bar" />

        <button
          type="button"
          id="theme-toggle"
          className="theme-toggle"
          onClick={toggle}
          aria-pressed={isLight}
          aria-label={isLight ? 'Dark өнгө рүү шилжих' : 'Light өнгө рүү шилжих'}
        >
          <span className="theme-icon theme-icon-moon" aria-hidden="true">🌙</span>
          <span className="theme-icon theme-icon-sun" aria-hidden="true">☀️</span>
        </button>
      </div>

      <a href={inviteUrl} className="btn btn-glow nav-invite" target="_blank" rel="noopener">
        {isEnglish ? 'Join server' : 'Server-т элсэх'}
      </a>

      <button
        type="button"
        id="nav-burger"
        className={`nav-burger${open ? ' open' : ''}`}
        onClick={() => setOpen((v) => !v)}
        aria-label={isEnglish ? 'Menu' : 'Цэс'}
        aria-expanded={open}
        aria-controls="primary-nav"
      >
        <span />
        <span />
        <span />
      </button>
    </nav>
  )
}