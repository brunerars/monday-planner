import { useEffect, useState, useRef, useCallback } from 'react'
import { useSearchParams, useNavigate, Link } from 'react-router-dom'
import '../styles/chat.css'
import { API_BASE as API } from '../config'

export default function ChatPage() {
  const [params] = useSearchParams()
  const navigate  = useNavigate()
  const leadId    = params.get('lead_id')

  // Session state
  const [sessionId, setSessionId]   = useState(null)
  const [config, setConfig]         = useState(null)
  const [messages, setMessages]     = useState([])
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState('')
  const [sending, setSending]       = useState(false)
  const [ended, setEnded]           = useState(false)
  const [ending, setEnding]         = useState(false)
  const [msgsUsed, setMsgsUsed]     = useState(0)
  const [msgsRemaining, setMsgsRemaining] = useState(0)
  const [input, setInput]           = useState('')
  const [showModal, setShowModal]   = useState(false)

  const messagesEndRef = useRef(null)
  const inputRef       = useRef(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  // ── Start session ──
  useEffect(() => {
    if (!leadId) {
      setError('Lead ID ausente. Volte ao formulário.')
      setLoading(false)
      return
    }

    let cancelled = false

    async function startSession() {
      try {
        const res = await fetch(`${API}/chat/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ lead_id: leadId }),
        })

        if (!res.ok) {
          const body = await res.json().catch(() => ({}))
          const detail = body?.detail

          // Session already active — reuse it
          if (res.status === 409 && detail?.code === 'SESSION_ACTIVE' && detail?.session_id) {
            if (!cancelled) {
              setSessionId(detail.session_id)
              await loadHistory(detail.session_id)
              setLoading(false)
            }
            return
          }

          throw new Error(detail?.message || `Erro ${res.status}`)
        }

        const data = await res.json()
        if (cancelled) return

        setSessionId(data.session_id)
        setConfig(data.config)
        setMsgsUsed(1) // greeting counts
        setMsgsRemaining(data.config.max_messages - 1)
        setMessages([{
          id: 'greeting',
          role: 'assistant',
          content: data.greeting,
        }])
        setLoading(false)
        setTimeout(() => inputRef.current?.focus(), 100)
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Erro ao iniciar sessão')
          setLoading(false)
        }
      }
    }

    startSession()
    return () => { cancelled = true }
  }, [leadId])

  // ── Load history for existing session ──
  async function loadHistory(sid) {
    try {
      const res = await fetch(`${API}/chat/history/${sid}`)
      if (!res.ok) throw new Error('Falha ao carregar histórico')
      const data = await res.json()

      setMessages(data.messages.map(m => ({
        id: m.id,
        role: m.role,
        content: m.content,
      })))
      setMsgsUsed(data.total_messages)
      setMsgsRemaining(Math.max(0, 15 - data.total_messages))

      if (data.status === 'completed') {
        setEnded(true)
      }
    } catch {
      setError('Erro ao carregar histórico do chat')
    }
  }

  // ── Send message ──
  const handleSend = useCallback(async () => {
    const text = input.trim()
    if (!text || !sessionId || sending || ended) return

    // Add user message optimistically
    const tempId = `user-${Date.now()}`
    setMessages(prev => [...prev, { id: tempId, role: 'user', content: text }])
    setInput('')
    setSending(true)
    setError('')

    try {
      const res = await fetch(`${API}/chat/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, content: text }),
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        const detail = body?.detail

        if (res.status === 429) {
          const retryAfter = detail?.retry_after_seconds || 5
          throw new Error(`Aguarde ${retryAfter}s antes de enviar outra mensagem`)
        }
        if (detail?.code === 'SESSION_EXPIRED') {
          setEnded(true)
          throw new Error('Sua sessão expirou por inatividade')
        }
        throw new Error(detail?.message || `Erro ${res.status}`)
      }

      const data = await res.json()

      // Add assistant response
      setMessages(prev => [...prev, {
        id: data.message_id,
        role: 'assistant',
        content: data.response,
      }])

      setMsgsUsed(data.session_status.messages_used)
      setMsgsRemaining(data.session_status.messages_remaining)

      // Session finalized (hit message limit)
      if (data.session_status.is_final) {
        setEnded(true)
        if (data.plan_trigger) {
          // Small delay so user can see the final message
          setTimeout(() => {
            navigateToPlan(data.plan_trigger.poll_url)
          }, 2500)
        }
      }
    } catch (err) {
      setError(err.message || 'Erro ao enviar mensagem')
    } finally {
      setSending(false)
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [input, sessionId, sending, ended])

  // ── End session manually ──
  async function handleEndSession() {
    if (!sessionId || ended || ending) return
    setEnding(true)
    setError('')

    try {
      const res = await fetch(`${API}/chat/end`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, reason: 'user_requested' }),
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body?.detail?.message || `Erro ${res.status}`)
      }

      const data = await res.json()
      setEnded(true)

      if (data.plan_trigger) {
        setTimeout(() => {
          navigateToPlan(data.plan_trigger.poll_url)
        }, 1500)
      }
    } catch (err) {
      setError(err.message || 'Erro ao encerrar sessão')
    } finally {
      setEnding(false)
    }
  }

  function handleGeneratePlan() {
    if (msgsUsed < 8) {
      setShowModal(true)
    } else {
      handleEndSession()
    }
  }

  function navigateToPlan(pollUrl) {
    // pollUrl is like "/api/v1/plans/status/{plan_id}"
    const planId = pollUrl.split('/').pop()
    navigate(`/plan/status?plan_id=${planId}`)
  }

  // ── Key handler ──
  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // ── Auto-resize textarea ──
  function handleInputChange(e) {
    setInput(e.target.value)
    // Auto-resize
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
  }

  // ── RENDER ──

  // Loading state
  if (loading) {
    return (
      <div className="chat-page">
        <header className="chat-header">
          <div className="chat-header-left">
            <Link to="/" className="chat-logo">MondayPlanner</Link>
          </div>
        </header>
        <div className="chat-loading">
          <div className="chat-loading-spinner" />
          <p className="chat-loading-text">Conectando com o especialista IA...</p>
        </div>
      </div>
    )
  }

  // Error state (no session)
  if (!sessionId && error) {
    return (
      <div className="chat-page">
        <header className="chat-header">
          <div className="chat-header-left">
            <Link to="/" className="chat-logo">MondayPlanner</Link>
          </div>
        </header>
        <div className="chat-loading">
          <span className="material-icons" style={{ fontSize: 48, color: 'var(--monday-red)' }}>error_outline</span>
          <p className="chat-loading-text">{error}</p>
          <Link to="/form" className="btn btn-primary" style={{ marginTop: '1rem', fontSize: 'var(--text-sm)' }}>
            Voltar ao formulário
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="chat-page">
      {/* Header */}
      <header className="chat-header">
        <div className="chat-header-left">
          <Link to="/" className="chat-logo">MondayPlanner</Link>
          <div className="chat-agent-badge">
            <span className="chat-agent-dot" />
            Especialista IA
          </div>
        </div>
        <div className="chat-header-right">
          {!ended && config?.cta_calendly_url && (
            <a
              className="chat-calendly-btn"
              href={config.cta_calendly_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              <span className="material-icons">event</span>
              <span>Agendar call</span>
            </a>
          )}
          {!ended && (
            <span className="chat-msg-counter">
              {msgsRemaining > 0
                ? `${msgsRemaining} msg restante${msgsRemaining !== 1 ? 's' : ''}`
                : 'Última mensagem'
              }
            </span>
          )}
          {!ended && (
            <button
              className="chat-end-btn"
              onClick={handleGeneratePlan}
              disabled={ending || msgsUsed < 4}
              title={msgsUsed < 4 ? 'Converse um pouco mais antes de gerar o plano' : 'Encerrar e gerar planejamento'}
            >
              <span className="material-icons">stop_circle</span>
              {ending ? 'Encerrando...' : 'Gerar plano'}
            </button>
          )}
        </div>
      </header>

      {/* Error toast */}
      {error && (
        <div className="chat-error">
          <span className="material-icons">warning</span>
          {error}
          <button className="chat-error-dismiss" onClick={() => setError('')}>
            <span className="material-icons">close</span>
          </button>
        </div>
      )}

      {/* Messages */}
      <div className="chat-messages">
        {messages.map(msg => (
          <div key={msg.id} className={`chat-msg chat-msg--${msg.role}`}>
            <div className="chat-msg-avatar">
              <span className="material-icons">
                {msg.role === 'assistant' ? 'smart_toy' : 'person'}
              </span>
            </div>
            <div className="chat-msg-bubble">
              {msg.content}
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {sending && (
          <div className="chat-typing">
            <div className="chat-msg-avatar" style={{ background: 'var(--almost-black)', color: 'var(--white)' }}>
              <span className="material-icons" style={{ fontSize: 14 }}>smart_toy</span>
            </div>
            <div className="chat-typing-bubble">
              <span className="chat-typing-dot" />
              <span className="chat-typing-dot" />
              <span className="chat-typing-dot" />
            </div>
          </div>
        )}

        {/* Session ended banner */}
        {ended && !sending && (
          <div className="chat-ended-banner">
            <p>Conversa encerrada. Seu planejamento está sendo gerado.</p>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="chat-input-area">
        <div className="chat-input-wrap">
          <textarea
            ref={inputRef}
            className="chat-input"
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder={ended ? 'Conversa encerrada' : 'Digite sua mensagem...'}
            disabled={ended || sending}
            rows={1}
          />
          <button
            className="chat-send-btn"
            onClick={handleSend}
            disabled={!input.trim() || ended || sending}
          >
            <span className="material-icons">send</span>
          </button>
        </div>
        {!ended && (
          <div className="chat-status-bar">
            Mensagem {msgsUsed} de {msgsUsed + msgsRemaining}
          </div>
        )}
      </div>

      {/* Confirmation modal for early plan generation */}
      {showModal && (
        <div className="chat-modal-overlay" onClick={() => setShowModal(false)}>
          <div className="chat-modal" onClick={e => e.stopPropagation()}>
            <h3 className="chat-modal-title">Gerar plano agora?</h3>
            <p className="chat-modal-text">
              Com poucas mensagens trocadas, o planejamento gerado pode ser mais superficial.
              Quanto mais contexto sobre sua operacao, melhor o resultado.
            </p>
            <div className="chat-modal-actions">
              <button
                className="chat-modal-btn chat-modal-btn--secondary"
                onClick={() => setShowModal(false)}
              >
                Continuar conversando
              </button>
              <button
                className="chat-modal-btn chat-modal-btn--primary"
                onClick={() => { setShowModal(false); handleEndSession() }}
              >
                Gerar mesmo assim
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
