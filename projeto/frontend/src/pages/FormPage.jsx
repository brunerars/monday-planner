import { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import FormProgress from '../components/form/FormProgress'
import FormStep1 from '../components/form/FormStep1'
import FormStep2 from '../components/form/FormStep2'
import FormStep3 from '../components/form/FormStep3'
import FormStep4 from '../components/form/FormStep4'
import '../styles/form.css'

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

  // Persist to localStorage on every change
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
  }, [data])

  // Send partial lead on beforeunload (step 3+ only)
  const sendPartial = useCallback(() => {
    if (step < 3 || !data.email) return
    const payload = JSON.stringify({
      step_completed: step,
      data: {
        empresa:       data.empresa,
        segmento:      data.segmento,
        tipo_negocio:  data.tipo_negocio,
        email:         data.email,
        nome_contato:  data.nome_contato,
      },
    })
    navigator.sendBeacon('/api/v1/leads/partial', new Blob([payload], { type: 'application/json' }))
  }, [step, data])

  useEffect(() => {
    window.addEventListener('beforeunload', sendPartial)
    return () => window.removeEventListener('beforeunload', sendPartial)
  }, [sendPartial])

  function handleChange(field, value) {
    setData(prev => ({ ...prev, [field]: value }))
    if (errors[field]) setErrors(prev => { const e = { ...prev }; delete e[field]; return e })
  }

  function handleNext() {
    const errs = validateStep(step, data)
    if (Object.keys(errs).length) { setErrors(errs); return }
    setErrors({})
    setStep(s => s + 1)
    window.scrollTo({ top: 0, behavior: 'smooth' })
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
      const res = await fetch('/api/v1/leads', {
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
