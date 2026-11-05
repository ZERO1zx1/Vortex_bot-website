import { useMemo } from 'react'
import { useRevealRef } from '../hooks/useMotion.js'

/**
 * Small shared primitives. Every one keeps the class names the existing
 * stylesheet targets, so the visual design is unchanged by the migration.
 */

/**
 * Wraps children in a `data-reveal` element that gains `.revealed` once it
 * scrolls into view.
 */
export function Reveal ({ as: Tag = 'div', className = '', children, ...rest }) {
  const ref = useRevealRef()
  return (
    <Tag ref={ref} data-reveal className={className} {...rest}>
      {children}
    </Tag>
  )
}

/** Renders one symbol from the sprite sheet at /img/icons.svg. */
export function Icon ({ name, className = '' }) {
  return (
    <svg
      className={className}
      viewBox='0 0 64 64'
      aria-hidden='true'
      focusable='false'
    >
      <use href={`/img/icons.svg#${name}`} />
    </svg>
  )
}

/** Section eyebrow + title block used by every section. */
export function SectionHead ({ tag, title, accent, children }) {
  return (
    <div className='section-head'>
      {tag ? <div className='section-tag'>{tag}</div> : null}
      <h2 className='section-title'>
        {title} {accent ? <span className='accent'>{accent}</span> : null}
      </h2>
      {children}
    </div>
  )
}

/* ------------------------------------------------------------------ *
 * Inline rich text
 * ------------------------------------------------------------------ */

const ALLOWED = new Set(['strong', 'em', 'b', 'i', 'br', 'code', 'span', 'a'])
const VOID = new Set(['br'])
const TAG_RE = /<(\/?)([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>/g

/**
 * Render a dictionary string that may contain a small set of inline tags.
 *
 * Translations legitimately carry markup — `<strong>`, `<span class="accent">`,
 * `<br>` — so emphasis survives a language switch. The string is tokenised and
 * rebuilt as real React elements rather than assigned to innerHTML, so no
 * dictionary content is ever treated as raw markup.
 *
 * Anything unbalanced or outside the allow-list degrades to plain text: a
 * malformed translation shows its characters instead of disappearing.
 */
export function RichText ({ text, className, ...rest }) {
  const content = useMemo(
    () => (typeof text === 'string' ? parseInline(text) : text ?? null),
    [text]
  )
  if (content === null) return null
  if (className || Object.keys(rest).length) {
    return (
      <span className={className} {...rest}>
        {content}
      </span>
    )
  }
  return content
}

/** Read one attribute value out of a raw tag. */
function attrValue (tag, name) {
  const m = tag.match(new RegExp(`\\b${name}\\s*=\\s*["']([^"']*)["']`, 'i'))
  return m ? m[1] : null
}

/** Only these schemes are honoured for dictionary links. */
function safeHref (href) {
  if (!href) return null
  const trimmed = href.trim()
  return /^(https?:|mailto:|\/|#)/i.test(trimmed) ? trimmed : null
}

/**
 * Build props for a parsed tag.
 *
 * The dictionary is authored content rather than user input, but it still
 * becomes real DOM attributes — so anchor hrefs get their scheme checked,
 * external targets are forced to `rel="noopener noreferrer"`, and no other
 * attribute is carried over. A rejected href degrades to plain text.
 */
function attrsFromTag (whole, tagName) {
  if (tagName === 'a') {
    const href = safeHref(attrValue(whole, 'href'))
    if (!href) return {}
    return /^https?:/i.test(href)
      ? { href, target: '_blank', rel: 'noopener noreferrer' }
      : { href }
  }
  const className = attrValue(whole, 'class')
  return className ? { className } : {}
}

function parseInline (source) {
  const root = { tag: null, attrs: {}, children: [] }
  const stack = [root]
  let cursor = 0
  let match

  TAG_RE.lastIndex = 0
  while ((match = TAG_RE.exec(source)) !== null) {
    const [whole, closing, rawTag] = match
    const tag = rawTag.toLowerCase()
    if (!ALLOWED.has(tag)) return source

    const top = stack[stack.length - 1]
    const chunk = source.slice(cursor, match.index)
    if (chunk) top.children.push(chunk)
    cursor = match.index + whole.length

    if (closing) {
      if (top.tag !== tag) return source
      stack.pop()
    } else if (VOID.has(tag)) {
      top.children.push({
        tag,
        attrs: {},
        children: [],
        key: `v${top.children.length}`
      })
    } else {
      const node = {
        tag,
        attrs: attrsFromTag(whole, tag),
        children: [],
        key: `n${top.children.length}`
      }
      top.children.push(node)
      stack.push(node)
    }
  }

  // Still-open tags mean the string is malformed.
  if (stack.length !== 1) return source

  const tail = source.slice(cursor)
  if (tail) root.children.push(tail)

  return materialize(root.children)
}

let keySeq = 0
function materialize (children) {
  return children.map((child, i) => {
    if (typeof child === 'string') return child
    const Tag =
      child.tag === 'b' ? 'strong' : child.tag === 'i' ? 'em' : child.tag
    // `<a>` without a safe href must not render as a link at all.
    if (Tag === 'a' && !child.attrs.href) return materialize(child.children)
    return (
      <Tag key={`${child.key ?? i}-${keySeq++}`} {...child.attrs}>
        {child.children.length ? materialize(child.children) : null}
      </Tag>
    )
  })
}
