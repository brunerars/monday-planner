const SEGMENTOS = [
  'Tecnologia & SaaS',
  'Consultoria & Serviços',
  'E-commerce & Varejo',
  'Saúde & Bem-estar',
  'Educação & Treinamento',
  'Imobiliário & Construção',
  'Indústria & Manufatura',
  'Marketing & Publicidade',
  'Financeiro & Contabilidade',
  'Alimentação & Gastronomia',
  'Outro',
]

const PORTES = [
  { value: 'MEI',    label: 'MEI'     },
  { value: 'ME',     label: 'ME'      },
  { value: 'EPP',    label: 'EPP'     },
  { value: 'Medio',  label: 'Médio'   },
  { value: 'Grande', label: 'Grande'  },
]

export default function FormStep1({ data, onChange, errors }) {
  return (
    <>
      <p className="form-step-label">Passo 1 de 4</p>
      <h2 className="form-title">Seu negócio</h2>
      <p className="form-subtitle">Vamos entender o perfil da sua empresa.</p>

      {/* Tipo de negócio */}
      <div className="form-group">
        <label className="form-label">Tipo de negócio</label>
        <div className="segmented">
          {['B2B', 'B2C'].map(tipo => (
            <button
              key={tipo}
              type="button"
              className={`segmented-btn${data.tipo_negocio === tipo ? ' active' : ''}`}
              onClick={() => onChange('tipo_negocio', tipo)}
            >
              {tipo}
            </button>
          ))}
        </div>
      </div>

      {/* Segmento */}
      <div className="form-group">
        <label className="form-label" htmlFor="segmento">Segmento</label>
        <select
          id="segmento"
          className={`form-select${errors.segmento ? ' has-error' : ''}`}
          value={data.segmento}
          onChange={e => onChange('segmento', e.target.value)}
        >
          <option value="">Selecione o segmento...</option>
          {SEGMENTOS.map(s => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        {errors.segmento && (
          <span className="form-error">
            <span className="material-icons">error_outline</span>
            {errors.segmento}
          </span>
        )}
      </div>

      {/* Empresa */}
      <div className="form-group">
        <label className="form-label" htmlFor="empresa">Nome da empresa</label>
        <input
          id="empresa"
          type="text"
          className={`form-input${errors.empresa ? ' has-error' : ''}`}
          placeholder="Ex: ARV Systems"
          value={data.empresa}
          onChange={e => onChange('empresa', e.target.value)}
          autoComplete="organization"
        />
        {errors.empresa && (
          <span className="form-error">
            <span className="material-icons">error_outline</span>
            {errors.empresa}
          </span>
        )}
      </div>

      {/* Porte */}
      <div className="form-group">
        <label className="form-label">
          Porte da empresa
          {errors.porte && (
            <span className="form-error" style={{ marginLeft: '.5rem' }}>
              <span className="material-icons">error_outline</span>
              {errors.porte}
            </span>
          )}
        </label>
        <div className={`chip-group${errors.porte ? ' has-error' : ''}`}>
          {PORTES.map(p => (
            <button
              key={p.value}
              type="button"
              className={`chip${data.porte === p.value ? ' selected' : ''}`}
              onClick={() => onChange('porte', p.value)}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>
    </>
  )
}
