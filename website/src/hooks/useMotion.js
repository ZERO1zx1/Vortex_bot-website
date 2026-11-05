import { useCallback, useEffect, useRef, useState } from 'react'
import { useMediaQuery } from '../lib/hooks.js'

const prefersReducedMotion = () =>
  typeof window !== 'undefined' &&
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

/**
 * Cursor-following 3D tilt. Returns a props object to spread onto the target
 * element. Disabled entirely for touch and reduced-motion users, matching the
 * legacy behaviour where listeners were simply never attached.
 */
export function useTilt ({ max = 9, scale = 1.02 } = {}) {
  const canHover = useMediaQuery('(hover: hover)')
  const enabled = canHover && !prefersReducedMotion()

  const onMouseMove = useCallback(
    event => {
      const el = event.currentTarget
      const r = el.getBoundingClientRect()
      const px = (event.clientX - r.left) / r.width
      const py = (event.clientY - r.top) / r.height
      const rx = (py - 0.5) * -max * 2
      const ry = (px - 0.5) * max * 2
      el.style.transform = `perspective(900px) rotateX(${rx.toFixed(
        2
      )}deg) rotateY(${ry.toFixed(2)}deg) translateZ(16px) scale(${scale})`
      el.style.setProperty('--gx', `${(px * 100).toFixed(1)}%`)
      el.style.setProperty('--gy', `${(py * 100).toFixed(1)}%`)
    },
    [max, scale]
  )

  const onMouseLeave = useCallback(event => {
    const el = event.currentTarget
    el.style.transform = ''
    el.style.removeProperty('--gx')
    el.style.removeProperty('--gy')
  }, [])

  const props = enabled
    ? { onMouseMove, onMouseLeave, 'data-tilt': '' }
    : { 'data-tilt': '' }
  return props
}

/** Animate a number from 0 to `target` once it scrolls into view. */
export function useCountUp (target, { duration = 1600, suffix = '' } = {}) {
  const [value, setValue] = useState(0)
  const ref = useRef(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return undefined

    if (prefersReducedMotion()) {
      setValue(target)
      return undefined
    }

    let raf = null
    const io = new IntersectionObserver(
      entries => {
        if (!entries[0].isIntersecting) return
        io.disconnect()
        const start = performance.now()
        const step = now => {
          const t = Math.min((now - start) / duration, 1)
          const eased = 1 - Math.pow(1 - t, 3)
          setValue(Math.round(target * eased))
          if (t < 1) raf = requestAnimationFrame(step)
        }
        raf = requestAnimationFrame(step)
      },
      { threshold: 0.4 }
    )
    io.observe(el)
    return () => {
      io.disconnect()
      if (raf) cancelAnimationFrame(raf)
    }
  }, [target, duration])

  return { ref, text: `${value}${suffix}` }
}

/** Scroll-linked vertical offset driven by `data-parallax` speed. */
export function useParallax (speed) {
  const ref = useRef(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return undefined
    let ticking = false
    const onScroll = () => {
      if (ticking) return
      ticking = true
      requestAnimationFrame(() => {
        el.style.transform = `translateY(${window.scrollY * speed * -0.12}px)`
        ticking = false
      })
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [speed])
  return ref
}

/**
 * Add `revealed` to an element the first time it enters the viewport.
 * Kept as a ref callback so it works with elements rendered by any component.
 */
export function useRevealRef () {
  return useCallback(node => {
    if (!node) return
    if (prefersReducedMotion()) {
      node.classList.add('revealed')
      return
    }
    const io = new IntersectionObserver(
      entries => {
        if (!entries[0].isIntersecting) return
        node.classList.add('revealed')
        io.disconnect()
      },
      { threshold: 0.01, rootMargin: '0px 0px -4% 0px' }
    )
    io.observe(node)
  }, [])
}

/**
 * Watches every `data-reveal` element in the document and adds `.revealed`
 * when it scrolls into view.
 *
 * A MutationObserver re-scans after renders so elements added later (the
 * command catalog re-renders on every search keystroke) are still animated.
 */
export function useRevealObserver (rootRef) {
  useEffect(() => {
    const root = rootRef.current
    if (!root) return undefined

    const io = new IntersectionObserver(
      entries => {
        entries.forEach(entry => {
          if (!entry.isIntersecting) return
          entry.target.classList.add('revealed')
          io.unobserve(entry.target)
        })
      },
      { threshold: 0.01, rootMargin: '0px 0px -4% 0px' }
    )

    const scan = () => {
      const nodes = root.querySelectorAll('[data-reveal]:not(.revealed)')
      if (prefersReducedMotion()) {
        nodes.forEach(n => n.classList.add('revealed'))
        return
      }
      nodes.forEach(n => io.observe(n))
    }

    scan()
    const mo = new MutationObserver(scan)
    mo.observe(root, { childList: true, subtree: true })

    return () => {
      io.disconnect()
      mo.disconnect()
    }
  }, [rootRef])
}
