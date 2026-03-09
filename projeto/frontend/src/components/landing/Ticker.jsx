const ITEMS = [
  'Planejamento em minutos',
  'Integração nativa Monday.com',
  'IA treinada para CRM',
  'Pipeline automático',
  'Entregável profissional',
  'Consultoria personalizada',
]

// Duplicamos para o loop infinito funcionar sem gap
const ALL = [...ITEMS, ...ITEMS]

export default function Ticker() {
  return (
    <div className="ticker" aria-hidden="true">
      <div className="ticker-inner">
        {ALL.map((item, i) => (
          <div key={i} className="ticker-item">
            <span className="ticker-dot" />
            {item}
          </div>
        ))}
      </div>
    </div>
  )
}
