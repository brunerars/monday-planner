const STEPS = [
  {
    number: '01',
    title: 'Preencha o formulário',
    desc: 'Conte sobre sua empresa, segmento e desafios em menos de 3 minutos.',
    chips: [
      { label: '4 etapas' },
      { label: '~3 min', variant: 'blue' },
    ],
  },
  {
    number: '02',
    title: 'Converse com a IA',
    desc: 'Nosso agente aprofunda seu contexto com perguntas estratégicas e personalizadas.',
    chips: [
      { label: 'até 15 msgs' },
      { label: 'IA Claude', variant: 'purple' },
    ],
  },
  {
    number: '03',
    title: 'Receba seu plano',
    desc: 'Planejamento completo no seu email, com board Monday pronto para execução.',
    chips: [
      { label: 'Monday.com', variant: 'green' },
      { label: 'Email' },
    ],
  },
]

export default function HowItWorks() {
  return (
    <section id="como-funciona" className="section">
      <div className="section-label reveal">Como funciona</div>
      <h2 className="section-title reveal">
        3 passos para seu<br />planejamento pronto
      </h2>

      <div className="steps-grid stagger">
        <div className="steps-connector" aria-hidden="true" />
        {STEPS.map((step) => (
          <div key={step.number} className="step-card reveal-scale">
            <div className="step-number">{step.number}</div>
            <h3 className="step-title">{step.title}</h3>
            <p className="step-desc">{step.desc}</p>
            <div className="step-chips">
              {step.chips.map((chip) => (
                <span
                  key={chip.label}
                  className={`step-chip${chip.variant ? ` step-chip--${chip.variant}` : ''}`}
                >
                  {chip.label}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
