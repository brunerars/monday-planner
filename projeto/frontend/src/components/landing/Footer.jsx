import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="footer">
      <span className="footer-logo" aria-label="MondayPlanner">MondayPlanner</span>

      <ul className="footer-links">
        <li><a href="#como-funciona">Como funciona</a></li>
        <li><a href="#beneficios">Benefícios</a></li>
        <li><Link to="/form">Começar agora</Link></li>
      </ul>

      <p className="footer-copy">
        © {new Date().getFullYear()} ARV Systems · Todos os direitos reservados
      </p>
    </footer>
  )
}
