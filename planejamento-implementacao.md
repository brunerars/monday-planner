# MondayPlanner — Planejamento de Implementação

**Projeto**: Plataforma de captação e planejamento inteligente para Monday.com
**Responsável**: Bruno — Head of Technology, ARV Systems
**Última atualização**: Março 2026

---

## Status Geral

| Fase | Descrição | Status |
|------|-----------|--------|
| 0 | Preparação e Setup | 🟡 Parcial |
| 1 | Frontend — LP + Form + Chat UI | ⏳ Aguardando design systems |
| 2 | Backend — Core + Agent | ✅ Completo |
| 3 | Integração (Make + Monday) | ✅ Revisado e fechado |
| 4 | Integração Front↔Back | ⬜ Pendente |
| 5 | Deploy + Go-live | 🟡 Infra pronta |
| 6 | Validação com leads reais | ⬜ Pós-launch |

---

## Fase 0 — Preparação e Setup

| Tarefa | Status | Observação |
|--------|--------|------------|
| 0.1 Repositório e estrutura | ✅ | Repo criado, estrutura de pastas completa |
| 0.2 Domínio e DNS | ⬜ | Manual: subdomínio → VPS → Traefik SSL |
| 0.3 Docker + PG + Redis no VPS | ✅ | docker-compose.yml + docker-compose.prod.yml prontos |
| 0.4 API keys | ⬜ | Manual: Anthropic key no `.env` do VPS |
| 0.5 Referência do site | ⬜ | Manual: escolher LP de referência (lapa.ninja) antes de iniciar Fase 1 |

---

## Fase 1 — Frontend

**Status**: ⏳ Aguardando design systems (Bruno)
**Dependência**: Design system LP + Design system Chat prontos

### O que vem quando os design systems chegarem

**1.1–1.2 Landing Page** (~4h)
- Adaptar referência com branding, conteúdo e seções:
  hero → como funciona (3 steps) → benefícios → CTA → form
- Mobile-first

**1.3 Multi-step Form** (~4h)
- 4 steps conforme `api-contracts.md` seção 1
- Validação client-side por step
- `localStorage` para persistência parcial entre steps
- Submit: `POST /api/v1/leads` com loading + erro 409 (email já existe) / 422

**1.5 Onboarding** (~1.5h)
- Tela de transição form → chat
- Cartão visual com resumo dos dados preenchidos
- Botão "Iniciar conversa" → `POST /api/v1/chat/start`

**1.4 Chat Interface** (~5h)
- Layout: sidebar (dados do lead) + área de chat
- Bubbles: usuário (direita) / agente (esquerda)
- Input bloqueado enquanto aguarda resposta (sem debounce necessário)
- Indicador "digitando..." durante chamada à API
- Contador discreto de mensagens restantes no topo
- Estados: IDLE → SENDING → RATE_LIMITED → GENERATING → PLAN_READY
- Tela GENERATING: progress bar + "Gerando seu planejamento..."
- Tela PLAN_READY: botão "Ver Planejamento" (abre `/plans/{id}/view`) + "Agendar Call" (Calendly)
- Mobile: chat full-screen, sidebar vira header colapsável

**1.6 Polish** (~1h)
- Testar fluxo completo em mobile (Chrome DevTools)
- Loading states, responsividade, performance

---

## Fase 2 — Backend ✅ Completo

**68 testes passando. Swagger em `/docs`.**

### Endpoints disponíveis

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/v1/leads` | Criar lead (form submit) |
| POST | `/api/v1/leads/partial` | Salvar form parcial (abandono) |
| GET | `/api/v1/leads/{id}` | Buscar lead por ID |
| PATCH | `/api/v1/leads/{id}/status` | Atualizar status do lead |
| POST | `/api/v1/chat/start` | Iniciar sessão de chat |
| POST | `/api/v1/chat/message` | Enviar mensagem (resposta do agente) |
| POST | `/api/v1/chat/end` | Encerrar sessão manualmente |
| GET | `/api/v1/chat/history/{id}` | Histórico completo da sessão |
| GET | `/api/v1/plans/status/{id}` | Polling de status da geração |
| GET | `/api/v1/plans/{id}` | Buscar plano completo (JSON) |
| GET | `/api/v1/plans/{id}/view` | Plano renderizado como HTML estilizado |
| GET | `/api/v1/plans/{id}/download` | Download do `.md` |
| GET | `/health` | Health check (DB + Redis) |

### Arquitetura implementada

```
app/
├── agent/
│   ├── prompts.py      # System prompt + PLAN_GENERATION_PROMPT + compression
│   ├── context.py      # Sliding window (8 msgs) + summary via Haiku + cache Redis
│   └── guardrails.py   # Tokens (max 500), msg limit (15), off-topic detection
├── models/             # SQLAlchemy 2.0: Lead, ChatSession, ChatMessage, Plan
├── schemas/            # Pydantic V2: request/response de leads, chat, plans
├── routers/            # leads.py, chat.py, plans.py (webhooks.py = stub)
├── services/
│   ├── lead_service.py   # CRUD + score calculation
│   ├── agent_service.py  # start_session, process_message, end_session
│   └── plan_service.py   # generate_plan + _notify_make (Make webhook)
└── utils/
    ├── redis_client.py   # Connection pool async
    ├── rate_limiter.py   # 3 msg/min por sessão, 100/min global
    └── security.py       # Email validation
```

### Variáveis de ambiente necessárias

```env
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
CLAUDE_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-20250514
MAKE_WEBHOOK_URL=https://hook.eu1.make.com/...   # Webhook notifica Make quando plano fica pronto
API_BASE_URL=https://planner.seudominio.com      # Usado para montar URLs no payload do Make
CTA_CALENDLY_URL=https://calendly.com/...        # Botão de call no HTML view e no email
CORS_ORIGINS=https://planner.seudominio.com
ENVIRONMENT=production
```

---

## Fase 3 — Integração (Revisada) ✅

**Estratégia simplificada — sem Monday service no backend.**

### O que foi implementado (código)
- `plan_service._notify_make()`: quando plano fica `generated`, faz POST para `MAKE_WEBHOOK_URL` com todos os dados do lead + links do plano. Fire-and-forget.
- `GET /plans/{id}/view`: página HTML estilizada com CTA — é o link que o Make inclui no email ao lead.

### O que Bruno configura manualmente (sem código)
- **Board "Pipeline MondayPlanner"** na Monday (via MCP — já validado): grupos Novo Lead → Planejamento Gerado → Call Agendada → Proposta Enviada → Fechado Ganho/Perdido
- **Make**: step 1 recebe webhook → cria item no board com dados do lead; step 2 envia email ao lead com link para `/plans/{id}/view`

### Entregável ao lead
O lead recebe email com link para a **página HTML do planejamento** (profissional, responsiva, com botão de agendamento de call). Bruno usa Claude Code + MCP Monday para criar o board de execução real do cliente antes/durante a call — esse é o diferencial competitivo.

---

## Fase 4 — Integração Front↔Back

**Status**: ⬜ Pendente (inicia após Fase 1 completa)
**Estimativa**: ~5h

- Form → `POST /api/v1/leads` (erros 409/422 tratados na UI)
- Onboarding → `POST /api/v1/chat/start` → armazena `session_id` no `sessionStorage`
- Chat → `POST /api/v1/chat/message` em loop; input bloqueado durante resposta
- Rate limit 429 → contador regressivo na UI antes de liberar input
- `is_final: true` → transição para tela GENERATING
- Polling `GET /plans/status/{id}` a cada 3s → quando `completed`, redireciona para `/plans/{id}/view`

---

## Fase 5 — Deploy

**Status**: 🟡 Infra pronta, aguarda domínio e Fase 4
**Estimativa**: ~2h de configuração

### Checklist de deploy
- [ ] `.env` preenchido no VPS (todas as vars acima)
- [ ] `docker stack deploy` via GitHub Actions no push para `main`
- [ ] `alembic upgrade head` automático no startup (já configurado no Dockerfile)
- [ ] Smoke test: form → chat → plano gerado → Make recebeu → email entregue
- [ ] UptimeRobot monitorando `/health`
- [ ] Testar em mobile (device real)

---

## Fase 6 — Validação com Leads Reais

**Meta**: 10 leads nos primeiros 7 dias após launch

| Canal | Ação |
|-------|------|
| LinkedIn | Post com screen recording do fluxo completo |
| Network pessoal | 5–10 empresas que precisam de organização/CRM |
| Cold outreach | DM para empresas médias no segmento-alvo |

**KPIs para validar a tese:**
- Taxa de conclusão do form: meta > 60%
- Taxa de conclusão do chat: meta > 40%
- Taxa de agendamento de call: meta > 20% dos planos gerados

**Após os primeiros leads:**
- Revisar qualidade do planejamento gerado (leitura manual)
- Ajustar system prompt conforme padrões de conversa reais
- Calibrar off-topic detection se necessário

---

## Caminho crítico até o go-live

```
Bruno: design system LP ──┐
Bruno: design system Chat ─┤
Bruno: 0.2 DNS/domínio ───┤
Bruno: 0.4 API keys ──────┤
Bruno: 0.5 referência ────┤
                           ↓
                     Fase 1 (frontend)
                           ↓
                     Fase 4 (integração)
                           ↓
                     Fase 5 (deploy)
                           ↓
                     Fase 6 (leads reais)
```

**Paralelo (pode fazer agora):**
- Criar board de pipeline na Monday (MCP)
- Configurar Make (webhook + email step)

---

## Decisões técnicas fixas (não mudar no MVP)

1. **Polling, não WebSocket** — simplicidade de deploy
2. **Sonnet 4, não Opus** — custo-benefício para conversação
3. **Chat text-only** — áudio/imagem é v1.5
4. **Form de 4 steps** — não adicionar campos
5. **15 mensagens hard limit** — protege custo, foca a conversa
6. **Input bloqueado durante resposta** — sem debounce, UX explícita
7. **HTML view, não PDF** — zero dependência, link enviado pelo Make
8. **Sem autenticação de usuário** — lead não precisa de conta
9. **Sem painel admin** — Monday Kanban é o painel
10. **Make como middleware de notificação** — sem Monday service no backend
