const BENEFITS = [
  {
    icon: 'bolt',
    title: 'Planejamento em minutos',
    desc: 'Sem reuniões demoradas. A IA gera um documento profissional com base no seu contexto real.',
  },
  {
    icon: 'space_dashboard',
    title: 'Board pronto no Monday',
    desc: 'Receba um pipeline completo configurado e pronto para sua equipe usar imediatamente.',
  },
  {
    icon: 'person_pin',
    title: '100% personalizado',
    desc: 'Cada planejamento é único. A IA adapta ao seu segmento, porte e maturidade digital.',
  },
  {
    icon: 'support_agent',
    title: 'Suporte especialista',
    desc: 'Após o planejamento, agende uma call com nosso time para implementar juntos.',
  },
]

export default function Benefits() {
  return (
    <section id="beneficios" className="section section--dark">
      <div className="section-label reveal">Por que MondayPlanner</div>
      <h2 className="section-title reveal">
        Não é só um formulário.<br />É sua estratégia pronta.
      </h2>

      <div className="benefits-grid stagger">
        {BENEFITS.map((b) => (
          <div key={b.title} className="benefit-card reveal-scale">
            <div className="benefit-icon">
              <span className="material-icons">{b.icon}</span>
            </div>
            <h3 className="benefit-title">{b.title}</h3>
            <p className="benefit-desc">{b.desc}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
