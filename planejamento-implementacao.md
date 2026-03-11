# MondayPlanner — Planejamento de Implementação

**Projeto**: Plataforma de captação e planejamento inteligente para Monday.com
**Responsável**: Bruno — Head of Technology, ARV Systems
**Última atualização**: 11 Mar 2026

---

## Status Geral

| Fase | Descrição | Status |
|------|-----------|--------|
| 0 | Preparação e Setup | ✅ Completo |
| 1 | Frontend — LP + Form + Chat UI | ✅ Completo |
| 2 | Backend — Core + Agent | ✅ Completo |
| 3 | Integração (Make + Monday) | 🟡 Config pendente (sem código) |
| 4 | Integração Front↔Back | ✅ Completo |
| 5 | Deploy + Go-live | ✅ Em produção |
| 6 | Validação com leads reais | 🟡 Em andamento |

---

## Fase 0 — Preparação e Setup ✅

| Tarefa | Status | Observação |
|--------|--------|------------|
| 0.1 Repositório e estrutura | ✅ | Repo criado, estrutura completa |
| 0.2 Domínio e DNS | ✅ | CNAME `monday-planner` → `manager.arvsystems.cloud` → Traefik SSL |
| 0.3 Docker + PG + Redis no VPS | ✅ | docker-compose.yml + docker-compose.prod.yml prontos |
| 0.4 API keys | ✅ | Todas as vars configuradas no Portainer |
| 0.5 Dev environment | ✅ | `docker compose up` sobe frontend + api + postgres + redis |

---

## Fase 1 — Frontend ✅ Completo

- Landing Page + Multi-step Form (4 steps) + Onboarding + Chat UI
- Recovery de form parcial: dados salvos no Redis (24h) + Postgres (step 3+)
- Frontend exibe prompt de recovery quando email já tem dados salvos
- Partial save agressivo em cada transição de step + beforeunload
- Favicon SVG personalizado (gradiente vermelho→roxo, neutro)

---

## Fase 2 — Backend ✅ Completo

**73 testes passando. Swagger em `/docs`.**

### Endpoints disponíveis

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/v1/leads` | Criar lead (form submit) |
| POST | `/api/v1/leads/partial` | Salvar form parcial (Redis + Postgres se email) |
| GET | `/api/v1/leads` | Listar todos os leads |
| GET | `/api/v1/leads/partial/recover` | Recuperar form parcial por email |
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

### Infraestrutura de dados

- **Leads parciais**: Redis (TTL 24h, recovery em tempo real) + Postgres (step 3+ com email, durável para automações)
- **Lead scoring**: calculado no cadastro (17-120 pts), enviado no payload Make
- **Plano gerado**: markdown + summary JSON, renderizado como HTML estilizado

---

## Fase 3 — Integração Make + Monday 🟡

### Código pronto ✅
- `plan_service._notify_make()`: POST ao `MAKE_WEBHOOK_URL` com payload completo (fire-and-forget)
- `GET /plans/{id}/view`: página HTML estilizada com CTA (link no email ao lead)
- `scripts/test_webhook_payload.py`: simula fluxo completo e imprime payload Make
- `MAKE_WEBHOOK_URL` configurada no .env ✅

### Payload enviado ao Make
```json
{
  "lead_id": "uuid",
  "empresa": "...",
  "nome_contato": "...",
  "email": "...",
  "whatsapp": "...",
  "segmento": "...",
  "tipo_negocio": "B2B/B2C",
  "porte": "...",
  "score": 55,
  "areas_interesse": ["Vendas", "Projetos"],
  "plan_id": "uuid",
  "plan_view_url": "https://api.monday-planner.arvsystems.cloud/api/v1/plans/{id}/view",
  "plan_download_url": "https://api.monday-planner.arvsystems.cloud/api/v1/plans/{id}/download",
  "summary": { ... }
}
```

### Pendente — Configurar no Make (sem código)
- [ ] **Cenário Make**: Webhook trigger → cria item no board Monday → envia email ao lead
- [ ] **Board Monday "Pipeline MondayPlanner"**: Novo Lead → Planejamento Gerado → Call Agendada → Proposta → Fechado
- [ ] **Template de email**: link para `plan_view_url` + CTA Calendly
- [ ] **Smoke test**: rodar `python scripts/test_webhook_payload.py --base-url https://api.monday-planner.arvsystems.cloud` → verificar item criado + email recebido

### Pendente — Automação n8n (partial leads)
- [ ] Cron job a cada 4h: busca `partial_leads` no Postgres que não viraram leads completos
- [ ] Dispara follow-up por email para leads que abandonaram no step 3+
- Ver `setup-n8n.md` para detalhes da query e workflow

---

## Fase 4 — Integração Front↔Back ✅ Completo

- Form → `POST /leads` (erros 409/422 tratados)
- Onboarding → `POST /chat/start` → `sessionStorage`
- Chat → `POST /chat/message` em loop; input bloqueado durante resposta
- Rate limit 429 → countdown na UI
- `is_final: true` → tela GENERATING
- Polling `GET /plans/status/{id}` a cada 3s → redireciona para `/plans/{id}/view`

---

## Fase 5 — Deploy ✅ Em produção

**URL**: `https://monday-planner.arvsystems.cloud`

### Checklist de deploy
- [x] Domínio + DNS configurado (CNAME → Traefik SSL automático)
- [x] `.env` carregado no Portainer (todas as vars)
- [x] CI/CD via GitHub Actions (push main → build images → push GHCR)
- [x] Stack criada no Portainer (Docker Swarm)
- [x] `alembic upgrade head` automático no startup (CMD do Dockerfile)
- [x] API + Frontend + Postgres + Redis rodando
- [ ] UptimeRobot monitorando `/health`
- [ ] Smoke test end-to-end em prod (form → chat → plano → Make → email)
- [ ] Testar em mobile (device real)

### Lições de deploy
- **Alpine + node_modules/.bin**: `chmod +x node_modules/.bin/*` necessário após `npm ci` em Dockerfiles Alpine
- **`.dockerignore`**: deve incluir `**/node_modules/` para evitar copiar deps locais do Windows
- **Primeiro deploy Swarm**: stack precisa ser criada manualmente no Portainer na primeira vez; deploys subsequentes são automáticos via CI

---

## Fase 6 — Validação com Leads Reais 🟡

**Meta**: 10 leads nos primeiros 7 dias após launch

| Canal | Ação |
|-------|------|
| LinkedIn | Post sobre o projeto (soft launch) |
| Network pessoal | 5–10 empresas que precisam de organização/CRM |
| Cold outreach | DM para empresas médias no segmento-alvo |

**KPIs:**
- Taxa de conclusão do form: meta > 60%
- Taxa de conclusão do chat: meta > 40%
- Taxa de agendamento de call: meta > 20% dos planos gerados

---

## Próximos passos

```
1. [Bruno] Configurar cenário Make (webhook → Monday item → email)
2. [Bruno] Criar board Pipeline na Monday
3. [Bruno] Smoke test end-to-end em prod com Make ativo
4. [Bruno] Automação n8n (partial leads follow-up)
5. [Bruno] UptimeRobot no /health
6. [Bruno] Divulgação LinkedIn + network
```

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

---

## Referências
- `CLAUDE.md` — guia técnico completo (stack, schemas, endpoints, regras)
- `setup-n8n.md` — guia de automações n8n (cron partial leads, payload Make, query SQL)
- `scripts/test_webhook_payload.py` — simula fluxo completo e imprime payload Make
- OpenAPI interativa em `https://api.monday-planner.arvsystems.cloud/docs`
