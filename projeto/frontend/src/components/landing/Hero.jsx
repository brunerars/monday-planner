import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'

import imgA from '../../../assets-monday/Work_management_new_1_b5c65dc82a79.png'
import imgB from '../../../assets-monday/hero-crm-new-top_PT-fixed_673027e3fc1f.png'
import imgC from '../../../assets-monday/tabs_leads_updated_PT_2cb5cc1a4981.png'

export default function Hero() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    let animId
    let particles = []

    const resize = () => {
      const dpr = window.devicePixelRatio || 1
      const w = canvas.offsetWidth
      const h = canvas.offsetHeight
      canvas.width  = w * dpr
      canvas.height = h * dpr
      ctx.scale(dpr, dpr)
      particles = Array.from({ length: 55 }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        r: Math.random() * 1.5 + .4,
        vx: (Math.random() - .5) * .22,
        vy: (Math.random() - .5) * .22,
        alpha: Math.random() * .12 + .03,
        color: Math.random() > .65 ? '200,42,42' : '97,97,255',
      }))
    }

    const draw = () => {
      const w = canvas.offsetWidth
      const h = canvas.offsetHeight
      ctx.clearRect(0, 0, w, h)
      for (const p of particles) {
        p.x += p.vx
        p.y += p.vy
        if (p.x < 0) p.x = w
        if (p.x > w) p.x = 0
        if (p.y < 0) p.y = h
        if (p.y > h) p.y = 0
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${p.color},${p.alpha})`
        ctx.fill()
      }
      animId = requestAnimationFrame(draw)
    }

    resize()
    draw()
    window.addEventListener('resize', resize, { passive: true })
    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('resize', resize)
    }
  }, [])

  return (
    <section className="hero">
      <canvas ref={canvasRef} className="hero-canvas" aria-hidden="true" />

      {/* Floating Monday.com screenshots */}
      <div className="hero-images" aria-hidden="true">
        <div className="hero-float hero-float--a">
          <img src={imgA} alt="" loading="eager" />
        </div>
        <div className="hero-float hero-float--b">
          <img src={imgB} alt="" loading="eager" />
        </div>
        <div className="hero-float hero-float--c">
          <img src={imgC} alt="" loading="eager" />
        </div>
      </div>

      {/* Glow rings */}
      <div className="hero-ring hero-ring--1" aria-hidden="true" />
      <div className="hero-ring hero-ring--2" aria-hidden="true" />

      {/* Content */}
      <div className="hero-content">
        <p className="hero-eyebrow">Planejamento Inteligente para Monday.com</p>

        <h1 className="hero-headline">
          <span className="line-outline">Seu negócio</span>
          <span className="line-solid">organizado</span>
          <span className="line-gradient">com IA</span>
        </h1>

        <div className="hero-meta">
          <p className="hero-desc">
            Converse com nosso agente, receba um planejamento personalizado
            e implemente no Monday.com em minutos.
          </p>
          <div className="hero-cta">
            <Link to="/form" className="btn btn-accent">
              Começar agora
              <span className="material-icons" style={{ fontSize: 18 }}>arrow_forward</span>
            </Link>
            <a href="#como-funciona" className="btn btn-ghost">
              Ver como funciona
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}
