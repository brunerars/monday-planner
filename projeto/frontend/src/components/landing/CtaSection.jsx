import { Link } from 'react-router-dom'

export default function CtaSection() {
  return (
    <section id="cta" className="cta-section">
      <p className="cta-label reveal">Comece agora</p>
      <h2 className="cta-title reveal">
        Pronto para organizar<br />sua empresa?
      </h2>
      <p className="cta-desc reveal">
        Leva menos de 10 minutos. Sem cartão de crédito. Sem compromisso.
      </p>
      <div className="cta-buttons reveal">
        <Link to="/form" className="btn btn-primary">
          Quero meu planejamento
          <span className="material-icons" style={{ fontSize: 18 }}>arrow_forward</span>
        </Link>
        <a
          href="/api/v1/plans/00000000-0000-0000-0000-000000000000/view"
          className="btn btn-outline"
          target="_blank"
          rel="noopener noreferrer"
        >
          Ver exemplo de plano
        </a>
      </div>
    </section>
  )
}
