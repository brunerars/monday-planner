const USA_MONDAY = [
  { value: 'sim',       label: 'Sim, já usamos'     },
  { value: 'avaliando', label: 'Estamos avaliando'  },
  { value: 'nao',       label: 'Ainda não'           },
]

const AREAS = [
  { value: 'Projetos',   label: 'Gestão de projetos'   },
  { value: 'Vendas',     label: 'Vendas & CRM'         },
  { value: 'RH',         label: 'RH & Pessoas'         },
  { value: 'Marketing',  label: 'Marketing'            },
  { value: 'Operacoes',  label: 'Operações'            },
  { value: 'Suporte',    label: 'Suporte ao cliente'   },
  { value: 'Financeiro', label: 'Financeiro'           },
]

export default function FormStep4({ data, onChange, errors }) {
  function toggleArea(value) {
    const current = data.areas_interesse || []
    const next = current.includes(value)
      ? current.filter(a => a !== value)
      : [...current, value]
    onChange('areas_interesse', next)
  }

  return (
    <>
      <p className="form-step-label">Passo 4 de 4</p>
      <h2 className="form-title">Seu contexto Monday</h2>
      <p className="form-subtitle">
        Últimas perguntas para personalizar seu planejamento.
      </p>

      {/* Usa Monday? */}
      <div className="form-group">
        <label className="form-label">Sua empresa já usa o Monday.com?</label>
        <div className="chip-group">
          {USA_MONDAY.map(opt => (
            <button
              key={opt.value}
              type="button"
              className={`chip${data.usa_monday === opt.value ? ' selected' : ''}`}
              onClick={() =>
                onChange('usa_monday', data.usa_monday === opt.value ? '' : opt.value)
              }
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Áreas de interesse */}
      <div className="form-group">
        <label className="form-label">
          Áreas de interesse{' '}
          <span className="form-label-opt">(selecione quantas quiser)</span>
        </label>
        <div className={`chip-group${errors.areas_interesse ? ' has-error' : ''}`}>
          {AREAS.map(area => (
            <button
              key={area.value}
              type="button"
              className={`chip chip--multi${
                (data.areas_interesse || []).includes(area.value) ? ' selected' : ''
              }`}
              onClick={() => toggleArea(area.value)}
            >
              {area.label}
            </button>
          ))}
        </div>
        {errors.areas_interesse && (
          <span className="form-error">
            <span className="material-icons">error_outline</span>
            {errors.areas_interesse}
          </span>
        )}
      </div>

      {/* Dor principal */}
      <div className="form-group">
        <label className="form-label" htmlFor="dor_principal">
          Qual é sua maior dor hoje?{' '}
          <span className="form-label-opt">(opcional)</span>
        </label>
        <textarea
          id="dor_principal"
          className="form-textarea"
          placeholder="Ex: Nossos projetos sempre atrasam e perdemos visibilidade do que cada área está fazendo..."
          value={data.dor_principal}
          onChange={e => onChange('dor_principal', e.target.value)}
          rows={4}
        />
      </div>
    </>
  )
}
