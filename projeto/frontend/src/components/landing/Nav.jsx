import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

export default function Nav() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <nav className={`nav${scrolled ? ' nav--scrolled' : ''}`}>
      <Link to="/" className="nav-logo">MondayPlanner</Link>

      <ul className="nav-links">
        <li><a href="#como-funciona">Como funciona</a></li>
        <li><a href="#beneficios">Benefícios</a></li>
        <li><a href="#cta">Contato</a></li>
      </ul>

      <Link to="/form" className="btn btn-primary nav-cta">
        Quero meu planejamento
      </Link>
    </nav>
  )
}
