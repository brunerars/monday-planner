import { useEffect, useState, useRef } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import '../styles/chat.css'

const API = '/api/v1'
const POLL_INTERVAL = 3000 // 3s

export default function PlanStatusPage() {
  const [params] = useSearchParams()
  const planId = params.get('plan_id')

  const [status, setStatus]     = useState('generating') // generating | generated | error
  const [plan, setPlan]         = useState(null)
  const [error, setError]       = useState('')
  const pollRef = useRef(null)

  useEffect(() => {
    if (!planId) {
      setError('Plan ID ausente.')
      return
    }

    pollStatus()
    pollRef.current = setInterval(pollStatus, POLL_INTERVAL)

    return () => clearInterval(pollRef.current)
  }, [planId])

  async function pollStatus() {
    try {
      const res = await fetch(`${API}/plans/status/${planId}`)
      if (!res.ok) throw new Error(`Erro ${res.status}`)
      const data = await res.json()

      setStatus(data.status)

      if (data.status === 'generated' || data.status === 'completed') {
        clearInterval(pollRef.current)
        setStatus('generated')
        // Load full plan data
        await loadPlan()
      }

      if (data.status === 'error') {
        clearInterval(pollRef.current)
        setError('Ocorreu um erro na geração do plano. Tente novamente mais tarde.')
      }
    } catch {
      // Don't stop polling on transient errors
    }
  }

  async function loadPlan() {
    try {
      const res = await fetch(`${API}/plans/${planId}`)
      if (!res.ok) throw new Error('Falha ao carregar plano')
      const data = await res.json()
      setPlan(data)
    } catch {
      // Plan data not critical for showing success
    }
  }

  const steps = [
    { label: 'Conversa finalizada', done: true },
    { label: 'Analisando contexto', done: status === 'generated' },
    { label: 'Gerando planejamento', done: status === 'generated' },
    { label: 'Pronto para download', done: status === 'generated' },
  ]

  // Find first not-done step to mark as active
  const activeIdx = steps.findIndex(s => !s.done)

  return (
    <div className="plan-page">
      <div className="plan-card">
        {/* Progress icon */}
        {status === 'generating' ? (
          <div className="plan-progress-ring">
            <div className="plan-progress-inner">
              <div className="chat-loading-spinner" />
            </div>
          </div>
        ) : status === 'generated' ? (
          <div className="plan-progress-ring plan-progress-ring--done">
            <span className="material-icons">check</span>
          </div>
        ) : (
          <div className="plan-progress-ring" style={{ background: 'var(--monday-red)' }}>
            <span className="material-icons">error_outline</span>
          </div>
        )}

        {/* Title */}
        <h1 className="plan-title">
          {status === 'generating' && 'Gerando seu planejamento...'}
          {status === 'generated' && 'Planejamento pronto!'}
          {status === 'error' && 'Ops, algo deu errado'}
        </h1>
        <p className="plan-subtitle">
          {status === 'generating' && 'Nosso especialista está criando um plano personalizado de implementação Monday.com para sua empresa.'}
          {status === 'generated' && (plan?.empresa
            ? `O plano de implementação da ${plan.empresa} está pronto para visualização.`
            : 'Seu plano personalizado está pronto para visualização.'
          )}
          {status === 'error' && error}
        </p>

        {/* Steps */}
        {status !== 'error' && (
          <div className="plan-steps">
            {steps.map((s, i) => {
              let state = 'pending'
              if (s.done) state = 'done'
              else if (i === activeIdx) state = 'active'

              return (
                <div key={i} className={`plan-step plan-step--${state}`}>
                  <div className={`plan-step-icon plan-step-icon--${state}`}>
                    {state === 'done' && <span className="material-icons">check</span>}
                    {state === 'active' && <span className="material-icons">autorenew</span>}
                    {state === 'pending' && <span className="material-icons">radio_button_unchecked</span>}
                  </div>
                  {s.label}
                </div>
              )
            })}
          </div>
        )}

        {/* CTAs */}
        {status === 'generated' && (
          <div className="plan-cta-group">
            <a
              href={`${API}/plans/${planId}/view`}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-primary"
              style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '.5rem' }}
            >
              <span className="material-icons" style={{ fontSize: 18 }}>visibility</span>
              Ver planejamento
            </a>
            <a
              href={`${API}/plans/${planId}/download`}
              className="btn-ghost"
              style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '.35rem' }}
            >
              <span className="material-icons" style={{ fontSize: 16 }}>download</span>
              Baixar .md
            </a>
          </div>
        )}

        {status === 'error' && (
          <div className="plan-cta-group">
            <Link to="/" className="btn-primary" style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
              Voltar ao início
            </Link>
          </div>
        )}

        {/* Summary stats */}
        {status === 'generated' && plan?.summary && (
          <div style={{
            marginTop: '1.5rem',
            padding: '1rem',
            background: 'var(--whitesmoke)',
            borderRadius: 'var(--radius-lg)',
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '.5rem',
            textAlign: 'center',
          }}>
            {plan.summary.boards != null && (
              <div>
                <div style={{ fontSize: 'var(--text-xl)', fontWeight: 800 }}>{plan.summary.boards}</div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--grey)' }}>Boards</div>
              </div>
            )}
            {plan.summary.automations != null && (
              <div>
                <div style={{ fontSize: 'var(--text-xl)', fontWeight: 800 }}>{plan.summary.automations}</div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--grey)' }}>Automações</div>
              </div>
            )}
            {plan.summary.integrations != null && (
              <div>
                <div style={{ fontSize: 'var(--text-xl)', fontWeight: 800 }}>{plan.summary.integrations}</div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--grey)' }}>Integrações</div>
              </div>
            )}
          </div>
        )}
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
