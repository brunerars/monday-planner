const ESTADOS = [
  'AC','AL','AP','AM','BA','CE','DF','ES','GO',
  'MA','MT','MS','MG','PA','PB','PR','PE','PI',
  'RJ','RN','RS','RO','RR','SC','SP','SE','TO',
]

const COLABORADORES = [
  { value: '1-5',     label: '1–5'     },
  { value: '6-10',    label: '6–10'    },
  { value: '11-50',   label: '11–50'   },
  { value: '51-200',  label: '51–200'  },
  { value: '201-500', label: '201–500' },
  { value: '500+',    label: '500+'    },
]

export default function FormStep2({ data, onChange }) {
  return (
    <>
      <p className="form-step-label">Passo 2 de 4</p>
      <h2 className="form-title">Localização & Equipe</h2>
      <p className="form-subtitle">
        Informações opcionais que ajudam a personalizar seu planejamento.
      </p>

      {/* Cidade + Estado */}
      <div className="form-row">
        <div className="form-group">
          <label className="form-label" htmlFor="cidade">
            Cidade <span className="form-label-opt">(opcional)</span>
          </label>
          <input
            id="cidade"
            type="text"
            className="form-input"
            placeholder="São Paulo"
            value={data.cidade}
            onChange={e => onChange('cidade', e.target.value)}
            autoComplete="address-level2"
          />
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="estado">
            Estado <span className="form-label-opt">(opcional)</span>
          </label>
          <select
            id="estado"
            className="form-select"
            value={data.estado}
            onChange={e => onChange('estado', e.target.value)}
          >
            <option value="">UF</option>
            {ESTADOS.map(uf => (
              <option key={uf} value={uf}>{uf}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Colaboradores */}
      <div className="form-group">
        <label className="form-label">
          Número de colaboradores <span className="form-label-opt">(opcional)</span>
        </label>
        <div className="chip-group">
          {COLABORADORES.map(c => (
            <button
              key={c.value}
              type="button"
              className={`chip${data.colaboradores === c.value ? ' selected' : ''}`}
              onClick={() =>
                onChange('colaboradores', data.colaboradores === c.value ? '' : c.value)
              }
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>
    </>
  )
}
