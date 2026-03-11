import { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import FormProgress from '../components/form/FormProgress'
import FormStep1 from '../components/form/FormStep1'
import FormStep2 from '../components/form/FormStep2'
import FormStep3 from '../components/form/FormStep3'
import FormStep4 from '../components/form/FormStep4'
import '../styles/form.css'
import { API_BASE as API } from '../config'

const STORAGE_KEY = 'mp_form_data'
const TOTAL_STEPS = 4

const INITIAL_DATA = {
  // Step 1
  tipo_negocio: 'B2B',
  segmento: '',
  empresa: '',
  porte: '',
  // Step 2
  cidade: '',
  estado: '',
  colaboradores: '',
  // Step 3
  nome_contato: '',
  email: '',
  whatsapp: '',
  cargo: '',
  // Step 4
  usa_monday: '',
  areas_interesse: [],
  dor_principal: '',
}

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return INITIAL_DATA
    return { ...INITIAL_DATA, ...JSON.parse(raw) }
  } catch {
    return INITIAL_DATA
  }
}

function validateStep(step, data) {
  const errs = {}
  if (step === 1) {
    if (!data.segmento)   errs.segmento = 'Selecione o segmento.'
    if (!data.empresa?.trim()) errs.empresa = 'Informe o nome da empresa.'
    if (!data.porte)      errs.porte = 'Selecione o porte.'
  }
  if (step === 3) {
    if (!data.nome_contato?.trim()) errs.nome_contato = 'Informe seu nome.'
    if (!data.email?.trim()) {
      errs.email = 'Informe o email.'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email)) {
      errs.email = 'Email inválido.'
    }
  }
  if (step === 4) {
    if (!data.areas_interesse?.length) errs.areas_interesse = 'Selecione ao menos uma área.'
  }
  return errs
}

export default function FormPage() {
  const navigate = useNavigate()
  const [step, setStep]       = useState(1)
  const [data, setData]       = useState(loadFromStorage)
  const [errors, setErrors]   = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const [recoveryPrompt, setRecoveryPrompt] = useState(null)

  // Persist to localStorage on every change
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
  }, [data])

  // Fire-and-forget partial save (used on step transitions + beforeunload)
  const sendPartial = useCallback(() => {
    if (step < 3 || !data.email) return
    const payload = JSON.stringify({
      step_completed: step,
      data: {
        empresa:       data.empresa,
        segmento:      data.segmento,
        tipo_negocio:  data.tipo_negocio,
        porte:         data.porte,
        email:         data.email,
        nome_contato:  data.nome_contato,
        whatsapp:      data.whatsapp,
        cargo:         data.cargo,
        cidade:        data.cidade,
        estado:        data.estado,
        colaboradores: data.colaboradores,
        usa_monday:    data.usa_monday,
        areas_interesse: data.areas_interesse,
        dor_principal: data.dor_principal,
      },
    })
    navigator.sendBeacon(`${API}/leads/partial`, new Blob([payload], { type: 'application/json' }))
  }, [step, data])

  useEffect(() => {
    window.addEventListener('beforeunload', sendPartial)
    return () => window.removeEventListener('beforeunload', sendPartial)
  }, [sendPartial])

  function handleChange(field, value) {
    setData(prev => ({ ...prev, [field]: value }))
    if (errors[field]) setErrors(prev => { const e = { ...prev }; delete e[field]; return e })
  }

  async function handleNext() {
    const errs = validateStep(step, data)
    if (Object.keys(errs).length) { setErrors(errs); return }
    setErrors({})

    // Recovery check: when leaving step 3 (email just validated)
    if (step === 3 && data.email) {
      try {
        const res = await fetch(`${API}/leads/partial/recover?email=${encodeURIComponent(data.email)}`)
        if (res.ok) {
          const saved = await res.json()
          // Only offer recovery if saved data has more progress
          if (saved.step_completed >= step && saved.data) {
            setRecoveryPrompt(saved)
            return
          }
        }
      } catch {
        // best-effort, continue normally
      }
    }

    advanceStep()
  }

  function advanceStep() {
    // Save partial on every step transition (fire-and-forget)
    sendPartial()
    setStep(s => s + 1)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function acceptRecovery() {
    if (!recoveryPrompt) return
    const saved = recoveryPrompt
    setData(prev => ({ ...prev, ...saved.data }))
    setRecoveryPrompt(null)
    // Jump to the step after the saved one, or at least step 4
    const targetStep = Math.min(Math.max(saved.step_completed + 1, step + 1), TOTAL_STEPS)
    setStep(targetStep)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function declineRecovery() {
    setRecoveryPrompt(null)
    advanceStep()
  }

  function handleBack() {
    setErrors({})
    setStep(s => s - 1)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  async function handleSubmit(e) {
    e.preventDefault()
    const errs = validateStep(step, data)
    if (Object.keys(errs).length) { setErrors(errs); return }

    setSubmitting(true)
    setSubmitError('')

    try {
      const res = await fetch(`${API}/leads`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tipo_negocio:    data.tipo_negocio,
          segmento:        data.segmento,
          empresa:         data.empresa,
          porte:           data.porte,
          cidade:          data.cidade   || undefined,
          estado:          data.estado   || undefined,
          colaboradores:   data.colaboradores || undefined,
          nome_contato:    data.nome_contato,
          email:           data.email,
          whatsapp:        data.whatsapp  || undefined,
          cargo:           data.cargo     || undefined,
          usa_monday:      data.usa_monday || undefined,
          areas_interesse: data.areas_interesse?.length ? data.areas_interesse : undefined,
          dor_principal:   data.dor_principal || undefined,
        }),
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body?.detail?.message || `Erro ${res.status}`)
      }

      const lead = await res.json()
      localStorage.removeItem(STORAGE_KEY)
      navigate(`/onboarding?lead_id=${lead.id}`)
    } catch (err) {
      setSubmitError(err.message || 'Não foi possível enviar. Tente novamente.')
    } finally {
      setSubmitting(false)
    }
  }

  const stepProps = { data, onChange: handleChange, errors }

  return (
    <div className="form-page">
      {/* Mini header */}
      <header className="form-mini-header">
        <Link to="/" className="form-logo">MondayPlanner</Link>
      </header>

      <main className="form-container">
        <FormProgress current={step} total={TOTAL_STEPS} />

        <form className="form-card" onSubmit={handleSubmit} noValidate>
          {step === 1 && <FormStep1 {...stepProps} />}
          {step === 2 && <FormStep2 {...stepProps} />}
          {step === 3 && <FormStep3 {...stepProps} />}
          {step === 4 && <FormStep4 {...stepProps} />}

          {recoveryPrompt && (
            <div className="recovery-prompt">
              <span className="material-icons" style={{ color: 'var(--primary)', fontSize: 22, verticalAlign: 'middle', marginRight: '.4em' }}>restore</span>
              <span>Encontramos dados salvos anteriormente para <strong>{recoveryPrompt.data.email}</strong>. Deseja continuar de onde parou?</span>
              <div style={{ display: 'flex', gap: '.5rem', marginTop: '.75rem' }}>
                <button type="button" className="btn btn-primary btn-sm" onClick={acceptRecovery}>
                  Sim, continuar
                </button>
                <button type="button" className="btn btn-ghost btn-sm" onClick={declineRecovery}>
                  Não, preencher novamente
                </button>
              </div>
            </div>
          )}

          {submitError && (
            <div className="submit-error">
              <span className="material-icons">error_outline</span>
              {submitError}
            </div>
          )}

          <div className="form-footer">
            <span className="form-step-count">
              {step < TOTAL_STEPS ? `Próximo: passo ${step + 1} de ${TOTAL_STEPS}` : 'Último passo'}
            </span>

            <div style={{ display: 'flex', gap: '.75rem' }}>
              {step > 1 && (
                <button type="button" className="btn btn-ghost" onClick={handleBack} disabled={submitting}>
                  Voltar
                </button>
              )}

              {step < TOTAL_STEPS ? (
                <button type="button" className="btn btn-primary" onClick={handleNext}>
                  Continuar
                </button>
              ) : (
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting
                    ? <><span className="material-icons form-spin" style={{ fontSize: 18, verticalAlign: 'middle', marginRight: '.4em' }}>autorenew</span>Enviando…</>
                    : 'Gerar meu planejamento'
                  }
                </button>
              )}
            </div>
          </div>
        </form>
      </main>
    </div>
  )
}
