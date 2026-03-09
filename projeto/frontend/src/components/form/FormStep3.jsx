export default function FormStep3({ data, onChange, errors }) {
  return (
    <>
      <p className="form-step-label">Passo 3 de 4</p>
      <h2 className="form-title">Seus dados</h2>
      <p className="form-subtitle">
        Para enviarmos o planejamento e entrarmos em contato.
      </p>

      {/* Nome */}
      <div className="form-group">
        <label className="form-label" htmlFor="nome_contato">Nome completo</label>
        <input
          id="nome_contato"
          type="text"
          className={`form-input${errors.nome_contato ? ' has-error' : ''}`}
          placeholder="Bruno Lima"
          value={data.nome_contato}
          onChange={e => onChange('nome_contato', e.target.value)}
          autoComplete="name"
        />
        {errors.nome_contato && (
          <span className="form-error">
            <span className="material-icons">error_outline</span>
            {errors.nome_contato}
          </span>
        )}
      </div>

      {/* Email */}
      <div className="form-group">
        <label className="form-label" htmlFor="email">Email profissional</label>
        <input
          id="email"
          type="email"
          className={`form-input${errors.email ? ' has-error' : ''}`}
          placeholder="voce@empresa.com"
          value={data.email}
          onChange={e => onChange('email', e.target.value)}
          autoComplete="email"
          inputMode="email"
        />
        {errors.email && (
          <span className="form-error">
            <span className="material-icons">error_outline</span>
            {errors.email}
          </span>
        )}
      </div>

      {/* WhatsApp */}
      <div className="form-group">
        <label className="form-label" htmlFor="whatsapp">
          WhatsApp <span className="form-label-opt">(opcional)</span>
        </label>
        <input
          id="whatsapp"
          type="tel"
          className="form-input"
          placeholder="+55 11 99999-9999"
          value={data.whatsapp}
          onChange={e => onChange('whatsapp', e.target.value)}
          autoComplete="tel"
          inputMode="tel"
        />
      </div>

      {/* Cargo */}
      <div className="form-group">
        <label className="form-label" htmlFor="cargo">
          Cargo <span className="form-label-opt">(opcional)</span>
        </label>
        <input
          id="cargo"
          type="text"
          className="form-input"
          placeholder="Head of Technology, CEO, Gerente..."
          value={data.cargo}
          onChange={e => onChange('cargo', e.target.value)}
          autoComplete="organization-title"
        />
      </div>
    </>
  )
}
