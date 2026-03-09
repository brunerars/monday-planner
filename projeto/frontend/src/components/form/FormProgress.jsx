export default function FormProgress({ current, total }) {
  return (
    <div className="form-progress" role="progressbar" aria-valuenow={current} aria-valuemax={total}>
      {Array.from({ length: total }, (_, i) => {
        const n = i + 1
        const done   = n < current
        const active = n === current
        return (
          <span key={n} style={{ display: 'contents' }}>
            <div className={`form-step-dot ${done ? 'done' : active ? 'active' : 'pending'}`}>
              {done
                ? <span className="material-icons" style={{ fontSize: 15 }}>check</span>
                : n
              }
            </div>
            {n < total && (
              <div className={`form-step-line${done ? ' done' : ''}`} />
            )}
          </span>
        )
      })}
    </div>
  )
}
