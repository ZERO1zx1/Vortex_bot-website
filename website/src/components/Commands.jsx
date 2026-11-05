import { useEffect, useRef, useState } from 'react'
import { CAT_META } from '../data/commands.js'
import { useLang } from '../hooks/useLang.jsx'
import {
  useCommandCatalog,
  categoryLabel,
  SLASH_COUNT,
  TOTAL_COUNT,
  TEXT_COUNT
} from '../hooks/useCommandCatalog.js'
import { SectionHead } from './primitives.jsx'

const prefixFor = command => (command.type === 'slash' ? '/' : 'A!')

/* ------------------------------- card ------------------------------- */

function CommandCard ({ command, index, onOpen }) {
  const { isEnglish, t } = useLang()
  const meta = CAT_META[command.cat] ?? {
    label: command.cat,
    color: '#89B4FA',
    icon: '🔧'
  }
  const description = isEnglish ? command.descEN || command.desc : command.desc

  return (
    <div
      className='cmd-card'
      style={{
        '--cat-color': meta.color,
        animationDelay: `${Math.min(index * 0.03, 0.5)}s`
      }}
      role='button'
      tabIndex={0}
      aria-label={`${prefixFor(command)}${command.name}`}
      onClick={() => onOpen(command)}
      onKeyDown={e => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onOpen(command)
        }
      }}
    >
      <span className='cmd-icon'>{command.icon}</span>
      <div className='cmd-body'>
        <span className='cmd-name'>
          {prefixFor(command)}
          {command.name}
        </span>
        <span className='cmd-desc'>{description}</span>
      </div>
      <span className='cmd-cat'>
        {meta.icon} {categoryLabel(command.cat, isEnglish)}
      </span>
      <span className={`cmd-type ${command.type}`}>
        {command.type === 'slash' ? 'SLASH' : 'TEXT'}
      </span>
    </div>
  )
}

/* ------------------------------- modal ------------------------------ */

function CommandModal ({ command, onClose }) {
  const { isEnglish, t } = useLang()
  const closeRef = useRef(null)
  const dialogRef = useRef(null)
  const restoreFocus = useRef(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    restoreFocus.current = document.activeElement
    closeRef.current?.focus()
    document.body.style.overflow = 'hidden'

    // Keep Tab inside the dialog while it is open.
    const onKey = e => {
      if (e.key === 'Escape') {
        onClose()
        return
      }
      if (e.key !== 'Tab' || !dialogRef.current) return
      const focusable = dialogRef.current.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      )
      if (!focusable.length) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
      restoreFocus.current?.focus?.()
    }
  }, [onClose])

  useEffect(() => {
    if (!copied) return undefined
    const t = setTimeout(() => setCopied(false), 1500)
    return () => clearTimeout(t)
  }, [copied])

  if (!command) return null

  const meta = CAT_META[command.cat] ?? {
    label: command.cat,
    color: '#89B4FA',
    icon: '🔧'
  }
  const args = Array.isArray(command.args) ? command.args : []
  const description = isEnglish ? command.descEN || command.desc : command.desc

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(command.example)
      setCopied(true)
    } catch {
      /* clipboard blocked — the example is on screen to copy by hand */
    }
  }

  return (
    <div className='cmd-modal open' id='cmd-modal'>
      <div className='cmd-modal-backdrop' onClick={onClose} />
      <div
        className='cmd-modal-box'
        role='dialog'
        aria-modal='true'
        ref={dialogRef}
        aria-labelledby='cmd-modal-title'
      >
        <button
          className='cmd-modal-close'
          aria-label={t('modal.close')}
          onClick={onClose}
          ref={closeRef}
        >
          ✕
        </button>

        <div className='cmd-modal-head'>
          <span className='cmd-modal-icon'>{command.icon}</span>
          <div>
            <div className='cmd-modal-name' id='cmd-modal-title'>
              {prefixFor(command)}
              {command.name}
            </div>
            <div className='cmd-modal-cat'>
              {meta.icon} {categoryLabel(command.cat, isEnglish)} ·{' '}
              <span className={`cmd-type ${command.type}`}>
                {command.type === 'slash' ? 'SLASH' : 'TEXT'}
              </span>
            </div>
          </div>
        </div>

        <div className='cmd-modal-body'>
          <p className='cmd-modal-desc'>{description}</p>

          {args.length > 0 ? (
            <div className='cmd-modal-row'>
              <div className='cmd-modal-label'>{t('modal.args')}</div>
              <div className='cmd-modal-args'>
                {args.map(arg => (
                  <span
                    key={arg.key}
                    className={`cmd-arg ${arg.req ? 'req' : 'opt'}`}
                  >
                    {arg.key}{' '}
                    <small>
                      {arg.req ? t('modal.required') : t('modal.optional')}
                    </small>
                  </span>
                ))}
              </div>
            </div>
          ) : null}

          {command.example ? (
            <div className='cmd-modal-row'>
              <div className='cmd-modal-label'>{t('modal.example')}</div>
              <div className='cmd-modal-example'>
                <code>{command.example}</code>
                <button
                  className='cmd-copy-btn'
                  type='button'
                  onClick={copy}
                  aria-label={copied ? '✓' : 'Copy example'}
                >
                  {copied ? '✅' : '📋'}
                </button>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}

/* ------------------------------ section ----------------------------- */

export function Commands () {
  const { t, isEnglish } = useLang()
  const {
    query,
    setQuery,
    category,
    setCategory,
    groups,
    isSearching,
    isEmpty,
    resultCount,
    clear
  } = useCommandCatalog()
  const [selected, setSelected] = useState(null)

  const categories = Object.keys(CAT_META)

  return (
    <section className='commands' id='commands'>
      <SectionHead tag={t('commands.tag')}>
        <span>
          {TOTAL_COUNT}{' '}
          <span className='accent'>{t('commands.breakdown_suffix')}</span> ·{' '}
          {SLASH_COUNT} slash / {TEXT_COUNT} text
        </span>
      </SectionHead>

      <div className='cmd-toolbar'>
        <label className='visually-hidden' htmlFor='cmd-search'>
          {t('commands.search_label')}
        </label>
        <input
          type='search'
          id='cmd-search'
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder={t('cmd.placeholder')}
          autoComplete='off'
        />

        <div
          className='cmd-filters'
          id='cmd-filters'
          role='group'
          aria-label={t('commands.filter_label')}
        >
          {categories.map(cat => {
            const meta = CAT_META[cat]
            return (
              <button
                key={cat}
                type='button'
                className={`filter${category === cat ? ' active' : ''}`}
                data-cat={cat}
                aria-pressed={category === cat}
                onClick={() => setCategory(cat)}
              >
                {meta.icon} {categoryLabel(cat, isEnglish)}
              </button>
            )
          })}
        </div>
      </div>

      <p className='cmd-result-count' role='status' aria-live='polite'>
        {resultCount > 0 ? `${resultCount} ${t('commands.results')}` : null}
        {/* The reset stays available whenever a filter is active, including
            when it matches nothing — otherwise a dead-end search can only be
            escaped by selecting and deleting the query by hand. */}
        {query.trim() || category !== 'all' ? (
          <>
            {resultCount > 0 ? ' · ' : null}
            <button type='button' className='cmd-reset' onClick={clear}>
              {t('commands.reset')}
            </button>
          </>
        ) : null}
      </p>

      <div className='cmd-grid' id='cmd-grid'>
        {isEmpty ? (
          <div className='cmd-empty'>
            {isSearching ? t('commands.empty') : t('commands.empty_cat')}
          </div>
        ) : (
          groups.map(group =>
            group.category === null ? (
              <div className='cmd-panels search-mode' key='search'>
                {group.commands.map((c, i) => (
                  <CommandCard
                    key={c.name}
                    command={c}
                    index={i}
                    onOpen={setSelected}
                  />
                ))}
              </div>
            ) : (
              <CategoryPanel
                key={group.category}
                category={group.category}
                commands={group.commands}
                isEnglish={isEnglish}
                onOpen={setSelected}
              />
            )
          )
        )}
      </div>

      {selected ? (
        <CommandModal command={selected} onClose={() => setSelected(null)} />
      ) : null}
    </section>
  )
}

function CategoryPanel ({ category, commands, isEnglish, onOpen }) {
  const meta = CAT_META[category]
  const slash = commands.filter(c => c.type === 'slash').length

  return (
    <div className='cmd-panel' style={{ '--cat-color': meta.color }}>
      <div className='panel-head'>
        <div className='panel-badge'>
          {meta.icon} {categoryLabel(category, isEnglish)}
        </div>
        <div className='panel-count'>
          {commands.length} команд · {slash} slash / {commands.length - slash}{' '}
          text
        </div>
      </div>
      <div className='panel-grid'>
        {commands.map((c, i) => (
          <CommandCard key={c.name} command={c} index={i} onOpen={onOpen} />
        ))}
      </div>
    </div>
  )
}
