import { useEffect, useRef } from 'react'

/** Layered sine sum — reads as an organic heartbeat rather than a plain wave. */
const wave = (x, t) =>
  Math.sin(x * 0.9 + t) * 0.32 +
  Math.sin(x * 1.7 + t * 1.6) * 0.14 +
  Math.sin(x * 3.1 + t * 0.7) * 0.07

/**
 * Animated activity graph on the live-status card.
 * Stops drawing when scrolled out of view or when the tab is hidden.
 */
export function useStatusGraph (ref, isOnline) {
  const onlineRef = useRef(isOnline)
  onlineRef.current = isOnline

  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return undefined
    const ctx = canvas.getContext('2d')
    if (!ctx) return undefined

    let W = 0
    let H = 0
    let t = 0
    let raf = null
    let visible = true
    const NODE_COUNT = 5

    const resize = () => {
      const r = canvas.getBoundingClientRect()
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      W = canvas.width = Math.max(1, Math.round(r.width * dpr))
      H = canvas.height = Math.max(1, Math.round(r.height * dpr))
    }
    resize()

    const draw = () => {
      raf = requestAnimationFrame(draw)
      if (!visible || document.hidden) return

      t += 0.02
      const online = onlineRef.current
      ctx.clearRect(0, 0, W, H)

      const amp = online ? 1 : 0.15
      const cA = online ? '137,180,250' : '243,139,168'
      const cB = online ? '148,226,213' : '243,139,168'

      ctx.strokeStyle = `rgba(${cA},0.07)`
      ctx.lineWidth = 1
      for (let i = 1; i < 4; i++) {
        ctx.beginPath()
        ctx.moveTo(0, (H / 4) * i)
        ctx.lineTo(W, (H / 4) * i)
        ctx.stroke()
      }

      const mid = H * 0.52
      const scale = H * 0.42

      const strokeGrad = ctx.createLinearGradient(0, 0, W, 0)
      strokeGrad.addColorStop(0, `rgba(${cA},0.95)`)
      strokeGrad.addColorStop(1, `rgba(${cB},0.95)`)

      ctx.beginPath()
      for (let px = 0; px <= W; px += 4) {
        const y = mid - wave((px / W) * 6, t) * scale * amp
        if (px === 0) ctx.moveTo(px, y)
        else ctx.lineTo(px, y)
      }
      ctx.strokeStyle = strokeGrad
      ctx.lineWidth = 2
      ctx.shadowColor = `rgba(${cA},0.8)`
      ctx.shadowBlur = 12
      ctx.stroke()
      ctx.shadowBlur = 0

      ctx.lineTo(W, H)
      ctx.lineTo(0, H)
      ctx.closePath()
      const fillGrad = ctx.createLinearGradient(0, 0, 0, H)
      fillGrad.addColorStop(0, `rgba(${cA},0.16)`)
      fillGrad.addColorStop(1, 'rgba(0,0,0,0)')
      ctx.fillStyle = fillGrad
      ctx.fill()

      for (let i = 0; i < NODE_COUNT; i++) {
        const p = (t * 0.06 + i / NODE_COUNT) % 1
        const x = p * W
        const y = mid - wave(p * 6, t) * scale * amp
        ctx.beginPath()
        ctx.fillStyle = `rgba(${cB},${(0.9 - p * 0.4).toFixed(2)})`
        ctx.shadowColor = `rgba(${cB},0.9)`
        ctx.shadowBlur = 10
        ctx.arc(x, y, 3, 0, Math.PI * 2)
        ctx.fill()
        ctx.shadowBlur = 0
      }
    }

    const io = new IntersectionObserver(
      entries => {
        visible = entries[0].isIntersecting
      },
      { threshold: 0.05 }
    )
    io.observe(canvas)

    window.addEventListener('resize', resize)
    draw()

    return () => {
      if (raf) cancelAnimationFrame(raf)
      io.disconnect()
      window.removeEventListener('resize', resize)
    }
  }, [ref])
}
