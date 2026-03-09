import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate, Link } from 'react-router-dom'
import '../styles/onboarding.css'

export default function OnboardingPage() {
  const [params] = useSearchParams()
  const navigate  = useNavigate()
  const leadId    = params.get('lead_id')

  const [nome, setNome] = useState('')

  // Fetch lead name for personalisation (best-effort)
  useEffect(() => {
    if (!leadId) return
    fetch(`/api/v1/leads/${leadId}`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data?.nome_contato) setNome(data.nome_contato.split(' ')[0]) })
      .catch(() => {})
  }, [leadId])

  // Redirect to /chat preserving lead_id
  function handleStart() {
    if (leadId) {
      navigate(`/chat?lead_id=${leadId}`)
    } else {
      navigate('/chat')
    }
  }

  const steps = [
    {
      icon: 'check',
      state: 'done',
      label: 'Formulário preenchido',
      desc: 'Seus dados foram recebidos com sucesso.',
    },
    {
      icon: '2',
      state: 'active',
      label: 'Conversa com o especialista IA',
      desc: 'Vamos entender melhor seu contexto em algumas perguntas rápidas.',
    },
    {
      icon: '3',
      state: 'pending',
      label: 'Planejamento personalizado',
      desc: 'Geração automática do seu plano de implementação Monday.com.',
    },
  ]

  return (
    <div className="ob-page">
      <div className="ob-card">
        {/* Check icon */}
        <div className="ob-check">
          <span className="material-icons">check</span>
        </div>

        {/* Headline */}
        <h1 className="ob-title">
          {nome ? (
            <>Tudo certo{', '}<span className="ob-name">{nome}</span>!</>
          ) : (
            'Tudo certo!'
          )}
        </h1>
        <p className="ob-subtitle">
          Recebemos suas informações. Agora é só uma conversa rápida com nosso
          especialista IA para gerarmos seu planejamento personalizado.
        </p>

        {/* Step tracker */}
        <div className="ob-steps">
          {steps.map((s, i) => (
            <div key={i} className={`ob-step${s.state === 'active' ? ' ob-step--active' : ''}`}>
              <div className={`ob-step-icon ob-step-icon--${s.state}`}>
                {s.state === 'done'
                  ? <span className="material-icons" style={{ fontSize: 18 }}>check</span>
                  : s.icon
                }
              </div>
              <div className="ob-step-body">
                <p className="ob-step-label">{s.label}</p>
                <p className="ob-step-desc">{s.desc}</p>
              </div>
            </div>
          ))}
        </div>

        {/* CTA */}
        <button className="btn-primary ob-cta" onClick={handleStart}>
          <span className="material-icons" style={{ fontSize: 20 }}>chat</span>
          Iniciar conversa
        </button>

        {/* Note */}
        <p className="ob-note">
          <span className="material-icons">schedule</span>
          Leva em média 3–5 minutos
        </p>
      </div>

      {/* Back link */}
      <Link
        to="/"
        style={{ marginTop: '1.5rem', fontSize: 'var(--text-xs)', color: 'var(--grey)', textDecoration: 'none', position: 'relative', zIndex: 1 }}
      >
        ← Voltar para o início
      </Link>
    </div>
  )
}
