# MondayPlanner — Guia de Execução Claude Code

## Projeto
Plataforma de captação de leads com formulário multi-step + chat IA + geração de planejamento.md para implementação Monday.com. Backend FastAPI, frontend separado (via workflow de site).

## Stack
- **Backend**: FastAPI 0.115.5 + Pydantic V2 + SQLAlchemy 2.0 (async) + asyncpg
- **Banco**: PostgreSQL 16
- **Cache**: Redis 7 (redis[asyncio])
- **IA**: Claude API (claude-sonnet-4-20250514) via anthropic SDK 0.40.0
- **Integração**: Make (webhook fire-and-forget) — sem GraphQL Monday no backend
- **Infra**: Docker Swarm + Traefik + Portainer

## Estrutura do projeto
```
monday-planner/                      # raiz do repositório
├── Dockerfile                       # multi-stage build (Python 3.12-slim)
├── docker-compose.yml               # dev: api + postgres:16 + redis:7
├── docker-compose.prod.yml          # Docker Swarm + Traefik
├── .github/workflows/deploy.yml     # CI/CD GitHub Actions
│
└── projeto/backend/                 # código da aplicação
    ├── requirements.txt
    ├── pytest.ini                   # asyncio_mode=auto, testpaths=tests
    ├── alembic.ini
    ├── alembic/versions/
    │   └── 048b50b598ce_initial_schema.py   # migration aplicada
    │
    ├── app/
    │   ├── main.py                  # FastAPI app + lifespan (Redis init/close)
    │   ├── config.py                # Settings via pydantic-settings
    │   ├── database.py              # engine + AsyncSessionLocal
    │   ├── dependencies.py          # get_db, get_redis_dep, verify_internal_api_key
    │   │
    │   ├── models/
    │   │   ├── base.py
    │   │   ├── lead.py
    │   │   ├── chat_session.py
    │   │   ├── chat_message.py
    │   │   └── plan.py
    │   │
    │   ├── schemas/
    │   │   ├── lead.py
    │   │   ├── chat.py
    │   │   └── plan.py
    │   │
    │   ├── routers/
    │   │   ├── leads.py             # POST /leads, POST /leads/partial, GET /leads/{id}, PATCH /leads/{id}/status
    │   │   ├── chat.py              # POST /chat/start, POST /chat/message, POST /chat/end, GET /chat/history/{id}
    │   │   ├── plans.py             # GET /plans/status/{id}, GET /plans/{id}, GET /plans/{id}/view, GET /plans/{id}/download
    │   │   └── webhooks.py          # stub vazio — implementação futura (Fase 3.4)
    │   │
    │   ├── services/
    │   │   ├── lead_service.py      # create_lead, get_lead, update_lead_status, create_partial_lead, calculate_score
    │   │   ├── agent_service.py     # start_session, process_message, end_session, get_history (CORE)
    │   │   ├── plan_service.py      # generate_plan, generate_plan_background, _notify_make, get_plan_status, get_plan
    │   │   └── monday_service.py    # stub vazio — implementação futura (Fase 3.2)
    │   │
    │   ├── agent/
    │   │   ├── prompts.py           # build_system_prompt(), build_plan_generation_prompt(), PENULTIMATE_NOTE, FINAL_NOTE, CONTEXT_COMPRESSION_PROMPT
    │   │   ├── context.py           # ContextManager (sliding window 8 msgs, summary via Haiku, Redis cache TTL 30min)
    │   │   └── guardrails.py        # GuardrailsChecker (tokens, msg limit, off-topic detection)
    │   │
    │   └── utils/
    │       ├── redis_client.py      # init_redis, close_redis, get_redis (singleton global)
    │       ├── rate_limiter.py      # check_session_rate_limit, check_global_rate_limit
    │       └── security.py          # email validation, sanitization
    │
    └── tests/
        ├── conftest.py              # fixtures: create_tables, test_redis, clean_tables, clean_redis, db_session, client
        ├── test_health.py
        ├── test_leads.py
        ├── test_chat.py
        └── test_agent.py
```

## Comandos

```bash
# Instalar dependências (dentro de projeto/backend/)
pip install -r requirements.txt

# Rodar testes (68 passando)
cd projeto/backend && python -m pytest tests/ -v

# Aplicar migrations
cd projeto/backend && alembic upgrade head

# Dev server
cd projeto/backend && uvicorn app.main:app --reload

# Docker dev (na raiz do repositório)
docker compose up -d

# Docker dev rebuild
docker compose up -d --build
```

## Variáveis de ambiente

| Variável | Obrigatória | Padrão | Descrição |
|---|---|---|---|
| `DATABASE_URL` | sim | `postgresql+asyncpg://mondayplanner:mondayplanner@localhost:5432/mondayplanner` | Conexão async com o Postgres |
| `REDIS_URL` | sim | `redis://localhost:6379/0` | Conexão Redis |
| `CLAUDE_API_KEY` | sim | `""` | Chave Anthropic |
| `CLAUDE_MODEL` | não | `claude-sonnet-4-20250514` | Modelo Claude |
| `MAKE_WEBHOOK_URL` | não | `""` | Webhook Make — notificação pós-geração do plano |
| `INTERNAL_API_KEY` | não | `""` | Proteção de endpoints internos |
| `API_BASE_URL` | não | `http://localhost:8000` | URL base usada para construir links do plano |
| `CTA_CALENDLY_URL` | não | `https://calendly.com/seulink/mondayplanner` | Link de agendamento no plano HTML |
| `CORS_ORIGINS` | não | `http://localhost:3000,http://localhost:5500` | Origens permitidas (vírgula-separadas) |
| `ENVIRONMENT` | não | `development` | `development` ou `production` |
| `LOG_LEVEL` | não | `debug` | Nível de log structlog |
| `AGENT_MAX_MESSAGES` | não | `15` | Hard limit de trocas por sessão |
| `AGENT_MAX_INPUT_TOKENS` | não | `500` | Máximo de tokens por mensagem de entrada |
| `AGENT_MAX_OUTPUT_TOKENS` | não | `800` | Máximo de tokens por resposta do agente |
| `AGENT_CONTEXT_WINDOW` | não | `8` | Tamanho da sliding window |
| `AGENT_SESSION_TIMEOUT_MINUTES` | não | `30` | TTL da sessão |
| `RATE_LIMIT_PER_SESSION` | não | `3` | Msgs por sessão por janela |
| `RATE_LIMIT_PER_SESSION_WINDOW_SECONDS` | não | `60` | Janela do rate limit por sessão |
| `RATE_LIMIT_GLOBAL` | não | `100` | Msgs globais por janela |
| `RATE_LIMIT_GLOBAL_WINDOW_SECONDS` | não | `60` | Janela do rate limit global |

## Regras de código
1. Async everywhere: todos os endpoints e services são async
2. Pydantic V2: usar model_validator, Field com examples, ConfigDict
3. SQLAlchemy 2.0: mapped_column, async session, sem legacy patterns
4. Dependency injection via FastAPI Depends()
5. Erros: HTTPException com detail estruturado (`{"code": "...", "message": "..."}`), nunca expor stacktrace
6. Logs: structlog com context (lead_id, session_id)
7. Config: variáveis de ambiente via pydantic-settings, nunca hardcoded
8. Redis: usar `redis[asyncio]` (importado como `redis.asyncio`) — não `aioredis` standalone

## Endpoints da API

Todos os endpoints são prefixados com `/api/v1`.

### Leads
| Método | Path | Descrição |
|---|---|---|
| POST | `/leads` | Criar lead (form completo) — 201 |
| POST | `/leads/partial` | Salvar form parcial em Redis (TTL 24h) — 201 |
| GET | `/leads/{lead_id}` | Buscar lead por UUID — 200 |
| PATCH | `/leads/{lead_id}/status` | Atualizar status do lead — 200 |

### Chat
| Método | Path | Descrição |
|---|---|---|
| POST | `/chat/start` | Iniciar sessão, gera greeting via Claude — 201 |
| POST | `/chat/message` | Enviar mensagem, retorna resposta do agente — 200 |
| POST | `/chat/end` | Encerrar sessão manualmente, dispara geração de plano — 200 |
| GET | `/chat/history/{session_id}` | Histórico completo de mensagens — 200 |

### Plans
| Método | Path | Descrição |
|---|---|---|
| GET | `/plans/status/{plan_id}` | Polling de status (`generating`/`completed`/`error`) — 200 |
| GET | `/plans/{plan_id}` | Plano completo (content_md + summary_json) — 200 |
| GET | `/plans/{plan_id}/view` | Renderiza plano como HTML estilizado (link enviado ao lead) — 200 |
| GET | `/plans/{plan_id}/download` | Download do arquivo `planejamento-{slug}.md` — 200 |

### Outros
| Método | Path | Descrição |
|---|---|---|
| GET | `/health` | Health check: DB + Redis status — 200 |

## Agent Service — Regras críticas
O `agent_service.py` é o core. Regras:

- System prompt vive em `agent/prompts.py` — função `build_system_prompt(lead)`
- Contexto do lead (dados do form) é injetado dinamicamente no system prompt
- Sliding window: system prompt + últimas 8 mensagens + summary das anteriores
- Summary gerado automaticamente via `claude-haiku-4-5-20251001` quando mensagens > 8 (chamada separada, max 300 tokens)
- Compressão ocorre na primeira vez que ultrapassa a janela e depois a cada 4 mensagens
- Hard limit: 15 trocas. Na mensagem 14 (penúltima), `PENULTIMATE_NOTE` é injetado no contexto. Na 15 (final), `FINAL_NOTE` é injetado e a sessão é encerrada automaticamente
- Claude API: retry exponencial 2x (`2^attempt` segundos), trata `RateLimitError`, `APIStatusError`, `APIConnectionError`
- Guardrails em `guardrails.py`: valida tokens de entrada (max 500, estimativa ~4 chars/token), detecta off-topic por keywords

Fluxo do `process_message()`:
```
1. Carrega sessão — erro SESSION_NOT_FOUND / SESSION_EXPIRED
2. Checa rate limit por sessão via Redis
3. Checa limite de mensagens via GuardrailsChecker
4. Valida tokens do input via GuardrailsChecker
5. Salva mensagem do usuário no DB
6. Monta contexto (sliding window via ContextManager)
7. Injeta PENULTIMATE_NOTE ou FINAL_NOTE se aplicável
8. Chama Claude API com retry
9. Salva resposta do agente no DB
10. Atualiza total_messages na sessão
11. Se is_final: encerra sessão (status=completed) + cria Plan record (status=generating)
12. Dispara compressão de contexto (non-blocking, após commit)
13. Retorna resposta
```

## Plan Service — Geração do planejamento.md
- Disparado pelo router via `BackgroundTasks` do FastAPI após `POST /chat/end` ou ao atingir msg 15
- `generate_plan_background()` cria engine/session próprios (a sessão do request já foi fechada)
- Lock Redis `plan:lock:{lead_id}` (TTL 300s, NX) evita geração duplicada
- Prompt `build_plan_generation_prompt(lead, conversation_history)` em `agent/prompts.py`
- Claude: `claude-sonnet-4-20250514`, max_tokens 4096, temperature 0.3
- Output esperado: markdown puro + linha `SUMMARY_JSON: {...}` ao final
- `_extract_summary()` separa content_md e summary_json (JSONB no banco)
- Após commit: chama `_notify_make()` (fire-and-forget, não bloqueia em caso de erro)

## Integração Make (substituiu monday_service)
`plan_service._notify_make()` faz POST ao `MAKE_WEBHOOK_URL` com:
```json
{
  "lead_id": "uuid",
  "empresa": "...",
  "nome_contato": "...",
  "email": "...",
  "whatsapp": "...",
  "segmento": "...",
  "tipo_negocio": "...",
  "porte": "...",
  "score": 0,
  "areas_interesse": [],
  "plan_id": "uuid",
  "plan_view_url": "https://.../api/v1/plans/{id}/view",
  "plan_download_url": "https://.../api/v1/plans/{id}/download",
  "summary": {}
}
```
Make é responsável por:
- Criar item no board de pipeline da Monday.com
- Enviar email ao lead com link do plano HTML

`monday_service.py` existe como stub vazio (Fase 3.2 futura).

## Redis Keys
```
chat:session:{session_id}     → HASH  (summary do contexto, TTL 30min)
chat:ratelimit:{session_id}   → COUNT (TTL 60s, max 3 por sessão)
chat:ratelimit:global         → COUNT (TTL 60s, max 100 global)
plan:lock:{lead_id}           → STR   (TTL 300s, evita geração duplicada)
lead:partial:{partial_id}     → STR   (JSON, TTL 24h — form abandonado)
```

## Schema do banco

### leads
| Coluna | Tipo | Notas |
|---|---|---|
| id | UUID PK | default uuid4 |
| tipo_negocio | VARCHAR(3) | "B2B" ou "B2C" |
| segmento | VARCHAR(100) | |
| empresa | VARCHAR(200) | |
| porte | VARCHAR(20) | "MEI","ME","EPP","Medio","Grande" |
| colaboradores | VARCHAR(50) | nullable |
| cidade | VARCHAR(100) | nullable |
| estado | VARCHAR(2) | nullable |
| nome_contato | VARCHAR(200) | |
| email | VARCHAR(200) | unique, indexed |
| whatsapp | VARCHAR(20) | nullable |
| cargo | VARCHAR(100) | nullable |
| usa_monday | VARCHAR(20) | nullable — "sim","nao","avaliando" |
| areas_interesse | JSONB | nullable |
| dor_principal | TEXT | nullable |
| monday_item_id | INTEGER | nullable — reservado para uso futuro |
| score | INTEGER | calculado em create_lead |
| status | VARCHAR(30) | indexed, default "novo" |
| created_at / updated_at | TIMESTAMPTZ | |

### chat_sessions
| Coluna | Tipo | Notas |
|---|---|---|
| id | UUID PK | |
| lead_id | UUID FK→leads | CASCADE, indexed |
| started_at | TIMESTAMPTZ | |
| ended_at | TIMESTAMPTZ | nullable |
| total_messages | INTEGER | contador bidirecional (user+assistant) |
| total_tokens_used | INTEGER | reservado |
| status | VARCHAR(20) | "active","completed" |
| context_summary | TEXT | nullable — fallback DB do summary Redis |

### chat_messages
| Coluna | Tipo | Notas |
|---|---|---|
| id | UUID PK | |
| session_id | UUID FK→chat_sessions | CASCADE, indexed |
| role | VARCHAR(10) | "user" ou "assistant" |
| content | TEXT | |
| content_type | VARCHAR(20) | default "text" |
| tokens_used | INTEGER | nullable |
| created_at | TIMESTAMPTZ | |

### plans
| Coluna | Tipo | Notas |
|---|---|---|
| id | UUID PK | |
| lead_id | UUID FK→leads | CASCADE, indexed |
| session_id | UUID FK→chat_sessions | nullable |
| empresa | VARCHAR(200) | desnormalizado para evitar JOIN |
| content_md | TEXT | |
| summary_json | JSONB | nullable — extraído do output do Claude |
| version | INTEGER | default 1 |
| status | VARCHAR(20) | "generating","generated","error" |
| created_at | TIMESTAMPTZ | |

## Testes
- **68 testes passando** em `tests/` (test_health.py, test_leads.py, test_chat.py, test_agent.py)
- `pytest.ini`: `asyncio_mode=auto`, `asyncio_default_fixture_loop_scope=session`
- `conftest.py`: drop_all + create_all por sessão de testes; Redis DB=1 para isolamento; limpeza por DELETE entre testes (respeita FK)
- Claude API é mockada nos testes de chat e agent via `unittest.mock.AsyncMock`

```bash
cd projeto/backend && python -m pytest tests/ -v
# Rodar apenas um arquivo
cd projeto/backend && python -m pytest tests/test_agent.py -v
```

## Docker e Deploy

### Dockerfile (raiz do repositório)
- Multi-stage build: builder (Python 3.12-slim + gcc + libpq-dev) → runtime (libpq5 apenas)
- Contexto de build: repositório raiz; copia `projeto/backend/` para `/app`
- CMD: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2`
- Usuário não-root: `appuser` (uid 1000)

### docker-compose.yml (dev)
- Serviços: `api`, `db` (postgres:16-alpine), `redis` (redis:7-alpine)
- Volume `./projeto/backend:/app` para hot-reload em dev
- Healthchecks em DB e Redis antes de subir a API

### docker-compose.prod.yml (Swarm)
- Imagem: `ghcr.io/brunerars/monday-planner:latest` (ou `$IMAGE`)
- Domínio: `planner.arvsystems.cloud` via Traefik + Let's Encrypt
- Replicas: 2 (API), 1 (DB e Redis)
- DB e Redis não expõem portas externamente
- Redis prod: `--maxmemory 256mb --maxmemory-policy allkeys-lru`

**Nota:** `docker-compose.prod.yml` ainda referencia `MONDAY_API_KEY`, `MONDAY_BOARD_ID` e `MONDAY_WEBHOOK_SECRET` como env vars — estas variáveis foram removidas do `config.py` na revisão da Fase 3. Atualizar o compose prod antes do próximo deploy.

## Ordem de execução para novas features
1. Schema/modelo → `app/models/` → nova migration Alembic
2. Schema Pydantic → `app/schemas/`
3. Service → `app/services/`
4. Router → `app/routers/` + registrar em `main.py`
5. Testes em `tests/`

## Não fazer
- Não usar sync database calls
- Não armazenar API keys no código
- Não expor endpoints sem rate limiting
- Não ultrapassar 15 mensagens por sessão
- Não gerar plano sem lock no Redis
- Não retornar erros internos ao frontend (sempre HTTPException com detail `{"code": "...", "message": "..."}`)
- Não usar `aioredis` standalone — usar `redis[asyncio]` (`import redis.asyncio as aioredis`)
- Não chamar `monday_service` diretamente — integração Monday vai via Make webhook

## O que ainda não foi implementado
- `app/routers/webhooks.py` — stub vazio, sem rotas ativas (Fase 3.4)
- `app/services/monday_service.py` — stub vazio (Fase 3.2)
- Upload de áudio/imagem — `media_service` não existe; `ChatConfig` já retorna `supports_audio=False`

## Referências
- `projeto.md` (raiz): referência completa do projeto — modelo de dados, board Monday, system prompt detalhado, estrutura do planejamento.md, estimativas de custo
- `planejamento-implementacao.md` (raiz): roadmap das fases de implementação
- OpenAPI interativa em `/docs` e `/redoc` quando a API estiver rodando
