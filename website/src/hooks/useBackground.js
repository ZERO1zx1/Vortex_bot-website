import { useEffect, useRef } from 'react'
import { useTheme } from './useTheme.jsx'

/** Read the brand particle hues straight from the CSS custom properties. */
function readHues () {
  const cs = getComputedStyle(document.documentElement)
  const n = name => parseFloat(cs.getPropertyValue(name)) || 218
  return [n('--particle-hue-a'), n('--particle-hue-b'), n('--particle-hue-c')]
}

/**
 * 2D particle fallback. Always mounts; the WebGL layer hides it via the
 * `bg-3d` body class once it takes over.
 */
export function useParticleCanvas (ref) {
  const { isLight } = useTheme()
  const isLightRef = useRef(isLight)
  isLightRef.current = isLight

  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return undefined
    const ctx = canvas.getContext('2d')
    if (!ctx) return undefined

    let W = 0
    let H = 0
    let particles = []
    let raf = null

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5)
      W = canvas.width = Math.round(window.innerWidth * dpr)
      H = canvas.height = Math.round(window.innerHeight * dpr)
      canvas.style.width = `${window.innerWidth}px`
      canvas.style.height = `${window.innerHeight}px`
    }

    const init = () => {
      resize()
      const [ha, hb, hc] = readHues()
      const count = Math.min(90, Math.floor((W * H) / 24000))
      particles = Array.from({ length: count }, () => ({
        x: Math.random() * W,
        y: Math.random() * H,
        vx: (Math.random() - 0.5) * 0.45,
        vy: (Math.random() - 0.5) * 0.45,
        r: Math.random() * 2.2 + 0.8,
        hue: Math.random() < 0.7 ? ha : Math.random() < 0.5 ? hb : hc
      }))
    }

    const draw = () => {
      raf = requestAnimationFrame(draw)
      // The WebGL layer owns the screen once it is running.
      if (document.body.classList.contains('bg-3d')) return

      const light = isLightRef.current
      ctx.clearRect(0, 0, W, H)

      for (const p of particles) {
        p.x += p.vx
        p.y += p.vy
        if (p.x < -10) p.x = W + 10
        if (p.x > W + 10) p.x = -10
        if (p.y < -10) p.y = H + 10
        if (p.y > H + 10) p.y = -10
      }

      const linkAlpha = light ? 0.14 : 0.18
      const lineColor = light ? 'rgba(59,94,168,' : 'rgba(137,180,250,'
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const a = particles[i]
          const b = particles[j]
          const dist = Math.hypot(a.x - b.x, a.y - b.y)
          if (dist >= 130) continue
          ctx.strokeStyle = `${lineColor}${(
            (1 - dist / 130) *
            linkAlpha
          ).toFixed(3)})`
          ctx.lineWidth = 0.7
          ctx.beginPath()
          ctx.moveTo(a.x, a.y)
          ctx.lineTo(b.x, b.y)
          ctx.stroke()
        }
      }

      const dotLight = light ? 72 : 78
      for (const p of particles) {
        ctx.fillStyle = `hsla(${p.hue}, 80%, ${dotLight}%, 0.85)`
        ctx.shadowColor = `hsla(${p.hue}, 80%, ${dotLight}%, 0.8)`
        ctx.shadowBlur = 10
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        ctx.fill()
      }
      ctx.shadowBlur = 0
    }

    init()
    draw()
    window.addEventListener('resize', init)
    return () => {
      window.removeEventListener('resize', init)
      if (raf) cancelAnimationFrame(raf)
    }
  }, [ref])
}

/**
 * WebGL particle field via three.js, loaded on demand from a CDN.
 * Falls back silently (leaving the 2D canvas up) when the CDN or WebGL is
 * unavailable, so the page never depends on it.
 */
export function useThreeBackground () {
  useEffect(() => {
    const THREE_URL =
      'https://cdn.jsdelivr.net/npm/three@0.164.1/build/three.module.js'
    const reduced = window.matchMedia?.(
      '(prefers-reduced-motion: reduce)'
    )?.matches
    let disposed = false
    let cleanup = null

    const start = async () => {
      if (disposed) return
      let THREE
      try {
        THREE = await import(/* @vite-ignore */ THREE_URL)
      } catch {
        return // CDN unreachable -> 2D canvas stays
      }
      if (disposed) return

      let renderer
      try {
        renderer = new THREE.WebGLRenderer({
          alpha: true,
          antialias: true,
          powerPreference: 'high-performance'
        })
      } catch {
        return // no WebGL -> 2D canvas stays
      }

      const canvas = renderer.domElement
      canvas.id = 'bg-3d'
      canvas.setAttribute('aria-hidden', 'true')
      document.body.appendChild(canvas)
      document.body.classList.add('bg-3d')

      const isLight = () =>
        document.documentElement.getAttribute('data-theme') === 'light'
      const isMobile = () => window.innerWidth <= 768

      const scene = new THREE.Scene()
      const camera = new THREE.PerspectiveCamera(70, 1, 0.1, 100)
      camera.position.z = 8

      const LIGHTNESS = () => (isLight() ? 66 : 78)
      const SIZE = () => (isLight() ? 0.075 : 0.05)

      const makeCloud = () => {
        const count = isMobile()
          ? 230
          : Math.min(
              720,
              Math.max(
                420,
                Math.floor((window.innerWidth * window.innerHeight) / 32000)
              )
            )
        const [ha, hb, hc] = readHues()
        const pos = new Float32Array(count * 3)
        const col = new Float32Array(count * 3)
        const spd = new Float32Array(count)
        const ph = new Float32Array(count)
        const c = new THREE.Color()
        const depth = 14

        for (let i = 0; i < count; i++) {
          pos[i * 3 + 0] = (Math.random() - 0.5) * 30
          pos[i * 3 + 1] = (Math.random() - 0.5) * 20
          pos[i * 3 + 2] = -2 + Math.random() * depth
          const hue = Math.random() < 0.72 ? ha : Math.random() < 0.5 ? hb : hc
          c.setHSL(
            (hue % 360) / 360,
            isLight() ? 0.55 : 0.72,
            LIGHTNESS() / 100
          )
          col[i * 3 + 0] = c.r
          col[i * 3 + 1] = c.g
          col[i * 3 + 2] = c.b
          spd[i] = (Math.random() - 0.5) * 0.02
          ph[i] = Math.random() * Math.PI * 2
        }

        const geo = new THREE.BufferGeometry()
        geo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
        geo.setAttribute('color', new THREE.BufferAttribute(col, 3))
        geo.userData = { pos, spd, ph }

        const mat = new THREE.PointsMaterial({
          size: SIZE(),
          sizeAttenuation: true,
          vertexColors: true,
          transparent: true,
          opacity: isLight() ? 0.55 : 0.8,
          depthWrite: false,
          blending: isLight() ? THREE.NormalBlending : THREE.AdditiveBlending
        })

        const points = new THREE.Points(geo, mat)
        scene.add(points)
        return { geo, points, mat, count }
      }

      let cloud = makeCloud()

      const recolor = () => {
        const light = isLight()
        cloud.mat.opacity = light ? 0.55 : 0.8
        cloud.mat.color.setRGB(1, 1, 1)
        cloud.mat.blending = light
          ? THREE.NormalBlending
          : THREE.AdditiveBlending
        cloud.mat.needsUpdate = true
        const [ha, hb, hc] = readHues()
        const col = cloud.geo.getAttribute('color')
        const c = new THREE.Color()
        for (let i = 0; i < cloud.count; i++) {
          const hue = Math.random() < 0.72 ? ha : Math.random() < 0.5 ? hb : hc
          c.setHSL((hue % 360) / 360, light ? 0.55 : 0.72, LIGHTNESS() / 100)
          col.setXYZ(i, c.r, c.g, c.b)
        }
        col.needsUpdate = true
        cloud.mat.size = SIZE()
        if (reduced) renderer.render(scene, camera)
      }

      const resize = () => {
        const w = window.innerWidth
        const h = window.innerHeight
        if (!w || !h) return
        camera.aspect = w / h
        camera.updateProjectionMatrix()
        renderer.setSize(w, h)
        renderer.setPixelRatio(
          Math.min(window.devicePixelRatio || 1, isMobile() ? 1.25 : 1.75)
        )
      }
      resize()

      let resizeTimer = null
      const onResize = () => {
        resize()
        clearTimeout(resizeTimer)
        resizeTimer = setTimeout(() => {
          scene.remove(cloud.points)
          cloud.geo.dispose()
          cloud.mat.dispose()
          cloud = makeCloud()
        }, 180)
      }
      window.addEventListener('resize', onResize)

      const themeObserver = new MutationObserver(recolor)
      themeObserver.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['data-theme']
      })

      let mouseX = 0
      let mouseY = 0
      let camX = 0
      let camY = 0
      const onMouseMove = e => {
        mouseX = (e.clientX / window.innerWidth - 0.5) * 2
        mouseY = (e.clientY / window.innerHeight - 0.5) * 2
      }
      window.addEventListener('mousemove', onMouseMove, { passive: true })

      let raf = null
      let t = 0
      const frame = () => {
        t += 0.005
        camX += (mouseX - camX) * 0.04
        camY += (mouseY - camY) * 0.04
        camera.position.x = camX * 0.9
        camera.position.y = -camY * 0.65
        camera.lookAt(0, 0, 0)

        const u = cloud.geo.userData
        const { pos, spd, ph } = u
        for (let i = 0; i < cloud.count; i++) {
          pos[i * 3 + 0] += spd[i] * 1.6 + Math.sin(t * 4 + ph[i]) * 0.004
          pos[i * 3 + 1] += spd[i] * 0.9 + Math.cos(t * 3 + ph[i]) * 0.003
          pos[i * 3 + 2] += spd[i] * 3
          const z = pos[i * 3 + 2]
          if (z > 14) pos[i * 3 + 2] = -2
          if (z < -2) pos[i * 3 + 2] = 13.99
          if (pos[i * 3 + 0] > 16) pos[i * 3 + 0] = -16
          if (pos[i * 3 + 0] < -16) pos[i * 3 + 0] = 16
          if (pos[i * 3 + 1] > 12) pos[i * 3 + 1] = -12
          if (pos[i * 3 + 1] < -12) pos[i * 3 + 1] = 12
        }
        cloud.geo.getAttribute('position').needsUpdate = true
        renderer.render(scene, camera)
        raf = requestAnimationFrame(frame)
      }

      const onVisibility = () => {
        if (document.hidden) {
          if (raf) {
            cancelAnimationFrame(raf)
            raf = null
          }
        } else if (!raf && !reduced) {
          raf = requestAnimationFrame(frame)
        }
      }
      document.addEventListener('visibilitychange', onVisibility)

      if (reduced) renderer.render(scene, camera)
      else raf = requestAnimationFrame(frame)

      cleanup = () => {
        if (raf) cancelAnimationFrame(raf)
        clearTimeout(resizeTimer)
        window.removeEventListener('resize', onResize)
        window.removeEventListener('mousemove', onMouseMove)
        document.removeEventListener('visibilitychange', onVisibility)
        themeObserver.disconnect()
        canvas.remove()
        document.body.classList.remove('bg-3d')
        renderer.dispose()
      }
    }

    start()

    return () => {
      disposed = true
      cleanup?.()
    }
  }, [])
}
