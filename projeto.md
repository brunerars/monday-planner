# MondayPlanner — Plataforma de Captação e Planejamento Inteligente para Monday.com

## 1. Visão do Produto

### O que é
Plataforma web que captura leads B2B/B2C, qualifica via formulário multi-step e conduz uma conversa com agente IA para estruturar o planejamento de implementação Monday.com do cliente. O output é um `planejamento.md` que serve como proposta técnica e âncora comercial.

### Proposta de valor
- **Para o lead**: recebe gratuitamente um planejamento estruturado de como organizar sua operação na Monday.com
- **Para nós**: lead chega auto-qualificado, com contexto completo, pronto pra call de fechamento — não de discovery

### Fluxo macro
```
[Landing Page] → [Multi-step Form] → [Onboarding do Chat] → [Conversa com Agente IA]
→ [Geração do planejamento.md] → [Lead registrado no Kanban Monday] → [Call comercial]
```

---

## 2. Arquitetura Técnica

### Stack
| Camada | Tecnologia |
|---|---|
| Frontend | HTML/CSS/JS (gerado via workflow site + referência) |
| Backend API | FastAPI + Pydantic V2 |
| Banco de dados | PostgreSQL (leads, sessões, histórico) |
| Cache/Fila | Redis (rate limiting, fila de mensagens, cache de sessão) |
| Agente IA | Claude API (claude-sonnet-4-20250514) |
| Integração | Monday.com API / MCP |
| Infra | Docker Swarm + Traefik + Portainer (Hostinger VPS) |
| CI/CD | GitHub Actions |

### Diagrama de componentes
```
┌─────────────────────────────────────────────────────┐
│                    FRONTEND                         │
│  Landing Page → Multi-step Form → Chat Interface    │
└──────────────────────┬──────────────────────────────┘
                       │ REST API (HTTPS)
┌──────────────────────▼──────────────────────────────┐
│                  FASTAPI BACKEND                    │
│                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │ Lead Router  │  │ Chat Router  │  │ Plan Gen  │  │
│  │ /api/leads   │  │ /api/chat    │  │ /api/plan │  │
│  └──────┬──────┘  └──────┬───────┘  └─────┬─────┘  │
│         │                │                │         │
│  ┌──────▼────────────────▼────────────────▼──────┐  │
│  │            Service Layer                      │  │
│  │  LeadService │ AgentService │ PlanService     │  │
│  └──────┬────────────────┬────────────────┬──────┘  │
│         │                │                │         │
│  ┌──────▼──┐  ┌──────────▼─────┐  ┌──────▼──────┐  │
│  │ Postgres │  │  Claude API    │  │   Redis     │  │
│  │ (dados)  │  │  (agente IA)   │  │ (fila/cache)│  │
│  └─────────┘  └────────────────┘  └─────────────┘  │
│         │                                           │
│  ┌──────▼──────────────────────────────────────┐    │
│  │         Monday.com API / MCP                │    │
│  │  (criação de leads no Kanban + boards)      │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

---

## 3. Módulos Detalhados

### 3.1 Multi-step Form (Frontend)

**Será construído via workflow de criação de site com referência.**

#### Steps do formulário:

**Step 1 — Tipo de negócio**
- Seleção: B2B ou B2C
- Campo: Segmento/Indústria (dropdown com opções principais + "Outro")

**Step 2 — Dados da empresa**
- Nome da empresa
- Porte (MEI / ME / EPP / Médio / Grande)
- Nº de colaboradores (faixa)
- Cidade/Estado

**Step 3 — Dados do contato**
- Nome completo
- E-mail corporativo
- WhatsApp (opcional)
- Cargo/Função

**Step 4 — Contexto operacional**
- "Já usa Monday.com?" (Sim / Não / Estou avaliando)
- "Quais áreas quer organizar?" (multi-select: Vendas, Projetos, RH, Financeiro, Marketing, Suporte, Operações)
- "Qual sua maior dor hoje?" (texto livre, max 280 chars)

**Regras:**
- Validação client-side em cada step
- Persistência parcial: se o lead abandona no step 3, ainda temos os dados dos steps 1-2
- Ao completar step 4 → POST /api/leads → redirect pro chat

#### Design/UX:
- Progress bar no topo
- Um step por vez, transição suave
- Mobile-first
- CTA claro em cada step: "Próximo →" / "Iniciar meu planejamento →"
- Tempo estimado visível: "Leva menos de 2 minutos"

---

### 3.2 Onboarding do Chat

Tela de transição entre o form e o chat. Objetivo: alinhar expectativa e ensinar o lead a usar.

**Conteúdo da tela de onboarding:**
```
"Pronto! Agora você vai conversar com nosso assistente de planejamento.

Ele vai te fazer algumas perguntas para entender melhor sua operação
e montar um plano personalizado de implementação Monday.com.

→ A conversa dura entre 5-10 minutos
→ Você pode enviar texto, áudio ou imagens
→ No final, você recebe seu planejamento completo

[Iniciar conversa]"
```

**Regras:**
- Mostra resumo dos dados que o lead já preencheu
- Botão "Editar dados" que volta pro form
- Não inicia chat sem aceite explícito

---

### 3.3 Agente IA (Core)

#### Modelo e configuração
- **Modelo**: claude-sonnet-4-20250514 (melhor custo-benefício para conversação estruturada)
- **Max tokens por resposta**: 800 (forçar respostas concisas)
- **Temperature**: 0.3 (consistência > criatividade)

#### System Prompt — Diretrizes do Agente

O agente tem um papel específico: **consultor de implementação Monday.com**. Ele NÃO é um chatbot genérico.

```
Você é um consultor especializado em implementação Monday.com.
Seu objetivo é conduzir uma conversa estruturada para entender a operação
do cliente e gerar um planejamento de implementação.

CONTEXTO DO LEAD (injetado dinamicamente):
- Tipo: {tipo_negocio}
- Segmento: {segmento}
- Empresa: {empresa}
- Porte: {porte}
- Colaboradores: {colaboradores}
- Áreas de interesse: {areas}
- Dor principal: {dor_principal}
- Usa Monday: {usa_monday}

COMPORTAMENTO:
1. Cumprimente brevemente usando o nome da empresa
2. Confirme a dor principal e aprofunde com 1-2 perguntas
3. Para cada área de interesse, faça perguntas específicas:
   - Vendas: funil atual, CRM existente, volume de leads/mês, ciclo de venda
   - Projetos: metodologia, tamanho do time, ferramentas atuais
   - RH: processos de contratação, onboarding, controle de ponto
   - Financeiro: fluxo de aprovação, controle de budget, relatórios
   - Marketing: campanhas, canais, métricas acompanhadas
   - Suporte: canais de atendimento, SLA, volume de tickets
   - Operações: processos core, gargalos, integrações necessárias
4. Pergunte sobre integrações existentes (ERP, email, WhatsApp, etc)
5. Pergunte sobre orçamento/expectativa de investimento (sem pressionar)
6. Ao ter informação suficiente, sinalize que vai gerar o planejamento

RESTRIÇÕES:
- Máximo de 15 trocas de mensagem (após isso, encerre e gere o plano)
- Não prometa funcionalidades específicas da Monday
- Não dê preços — direcione para a call
- Se o lead desviar do assunto, reconduza educadamente
- Respostas curtas e objetivas: máximo 3 parágrafos por mensagem
- Faça no máximo 2 perguntas por mensagem

FORMATO:
- Tom: profissional mas acessível
- Sem emojis excessivos
- Use bullet points quando listar opções
- Sempre termine com uma pergunta (exceto na mensagem final)
```

#### Estratégia de controle de tokens

| Mecanismo | Implementação |
|---|---|
| Max mensagens por sessão | 15 trocas (hard limit) |
| Max tokens input do lead | 500 tokens por mensagem |
| Max tokens resposta do agente | 800 tokens |
| Context window management | Sliding window: mantém system prompt + últimas 8 mensagens + resumo das anteriores |
| Rate limiting | Redis: max 3 msg/min por sessão |
| Sessão expirada | 30 min de inatividade → encerra e gera plano parcial |
| Estimativa de custo | ~$0.02-0.05 por sessão completa (Sonnet) |

#### Suporte multi-modal

**Áudio:**
- Frontend captura via MediaRecorder API
- Envia como blob para backend
- Backend transcreve via Whisper API (ou alternativa) → texto → agente
- Limite: 60s por áudio

**Imagem:**
- Lead pode enviar screenshots de ferramentas atuais, planilhas, fluxos
- Backend envia como input visual pro Claude (vision)
- Limite: 3 imagens por sessão, max 2MB cada

**Arquivo:**
- Aceitar: .xlsx, .csv, .pdf (planilhas de processos, organogramas)
- Backend extrai texto/dados relevantes → injeta no contexto
- Limite: 1 arquivo por sessão, max 5MB

---

### 3.4 Geração do planejamento.md

Ao encerrar a conversa (por limite de mensagens ou decisão do agente), o sistema gera o documento.

#### Estrutura do planejamento.md

```markdown
# Planejamento de Implementação Monday.com
## {nome_empresa} — {segmento}

**Gerado em**: {data}
**Consultor IA**: MondayPlanner v1.0

---

## 1. Contexto da Empresa
- Porte / colaboradores / segmento
- Situação atual (ferramentas, processos, dores)

## 2. Objetivos Identificados
- Lista priorizada dos objetivos do cliente

## 3. Estrutura Proposta na Monday.com

### 3.1 Workspaces
- Workspace X: descrição e propósito

### 3.2 Boards
Para cada board:
- Nome e propósito
- Colunas sugeridas (tipo + nome)
- Grupos (categorias/etapas)
- Views recomendadas (Kanban, Timeline, Dashboard)

### 3.3 Automações Sugeridas
- Automação 1: trigger → ação → benefício
- Automação 2: ...

### 3.4 Integrações Recomendadas
- Integração 1: ferramenta → tipo de conexão → dados sincronizados

## 4. Roadmap de Implementação
- Fase 1 (Semana 1-2): Setup básico
- Fase 2 (Semana 3-4): Automações e integrações
- Fase 3 (Semana 5-6): Treinamento e ajustes

## 5. Estimativa de Licenças Monday.com
- Plano recomendado: {Standard/Pro/Enterprise}
- Nº de usuários: {n}
- Custo mensal estimado: R$ {valor}
- Obs: valores sujeitos a confirmação

## 6. Próximos Passos
→ Agendar call de alinhamento com nosso time
→ [Link para agendamento]
```

#### Geração técnica:
- Prompt dedicado com todo o contexto da conversa
- Modelo: claude-sonnet-4-20250514 com max_tokens 4096
- Output em markdown puro
- Salvo no PostgreSQL + disponibilizado como download

---

### 3.5 Integração Monday.com (Kanban de Leads)

Ao gerar o planejamento, o lead é automaticamente registrado num board Kanban na Monday.

#### Estrutura do Board: "Pipeline MondayPlanner"

**Grupos (colunas do Kanban):**
1. Novo Lead
2. Planejamento Gerado
3. Call Agendada
4. Proposta Enviada
5. Fechado-Ganho
6. Fechado-Perdido

**Colunas do item:**
| Coluna | Tipo | Conteúdo |
|---|---|---|
| Lead | Name | Nome do contato |
| Empresa | Text | Nome da empresa |
| Segmento | Dropdown | Segmento selecionado |
| Tipo | Status | B2B / B2C |
| Porte | Dropdown | MEI/ME/EPP/Médio/Grande |
| Áreas | Tags | Áreas de interesse |
| Dor Principal | Long Text | Texto do form |
| E-mail | Email | Email do lead |
| WhatsApp | Phone | Telefone |
| Plano Sugerido | Status | Standard/Pro/Enterprise |
| Custo Estimado | Numbers | Valor mensal estimado |
| Score | Numbers | Score de qualificação (calculado) |
| Planejamento | Link | URL do planejamento.md |
| Data Entrada | Date | Timestamp de criação |

**Automações do board:**
- Quando status muda para "Call Agendada" → notifica responsável
- Quando item criado → atribui responsável por round-robin
- Quando status = "Fechado-Ganho" → move para board "Clientes Ativos"
- Se item em "Planejamento Gerado" por +48h sem mudança → notifica follow-up

**Implementação:**
- Via Monday.com API (REST) no backend
- Alternativa: via MCP se executando com Claude Code
- Webhook da Monday para atualizar status no PostgreSQL local

---

## 4. Modelo de Dados (PostgreSQL)

```sql
-- Leads capturados pelo formulário
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo_negocio VARCHAR(3) NOT NULL, -- B2B / B2C
    segmento VARCHAR(100) NOT NULL,
    empresa VARCHAR(200) NOT NULL,
    porte VARCHAR(20) NOT NULL,
    colaboradores VARCHAR(50),
    cidade VARCHAR(100),
    estado VARCHAR(2),
    nome_contato VARCHAR(200) NOT NULL,
    email VARCHAR(200) NOT NULL UNIQUE,
    whatsapp VARCHAR(20),
    cargo VARCHAR(100),
    usa_monday VARCHAR(20),
    areas_interesse JSONB, -- ["Vendas", "Projetos", ...]
    dor_principal TEXT,
    monday_item_id BIGINT, -- ID do item no board Monday
    score INTEGER DEFAULT 0,
    status VARCHAR(30) DEFAULT 'novo',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sessões de chat com o agente
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    total_messages INTEGER DEFAULT 0,
    total_tokens_used INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active', -- active / completed / expired / error
    context_summary TEXT -- resumo comprimido pra sliding window
);

-- Mensagens individuais do chat
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(10) NOT NULL, -- user / assistant
    content TEXT NOT NULL,
    content_type VARCHAR(20) DEFAULT 'text', -- text / audio / image / file
    tokens_used INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Planejamentos gerados
CREATE TABLE plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
    session_id UUID REFERENCES chat_sessions(id),
    content_md TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'generated', -- generated / sent / viewed
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_leads_email ON leads(email);
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_sessions_lead ON chat_sessions(lead_id);
CREATE INDEX idx_messages_session ON chat_messages(session_id);
CREATE INDEX idx_plans_lead ON plans(lead_id);
```

---

## 5. API Endpoints

### Leads
```
POST   /api/v1/leads              — Criar lead (form submit)
GET    /api/v1/leads/{id}         — Buscar lead
PATCH  /api/v1/leads/{id}/status  — Atualizar status
```

### Chat
```
POST   /api/v1/chat/start         — Iniciar sessão (recebe lead_id)
POST   /api/v1/chat/message       — Enviar mensagem (texto)
POST   /api/v1/chat/upload        — Enviar mídia (áudio/imagem/arquivo)
GET    /api/v1/chat/history/{id}  — Histórico da sessão
POST   /api/v1/chat/end           — Encerrar sessão manualmente
```

### Planejamento
```
POST   /api/v1/plans/generate     — Gerar planejamento (a partir de sessão)
GET    /api/v1/plans/{id}         — Buscar planejamento
GET    /api/v1/plans/{id}/download — Download do .md
```

### Webhooks
```
POST   /api/v1/webhooks/monday    — Receber atualizações da Monday
```

---

## 6. Fila Redis e Resiliência

### Estrutura de filas

```
# Fila de mensagens pendentes (se Claude API demorar/cair)
chat:queue:{session_id} → LIST de mensagens aguardando processamento

# Cache de sessão ativa (evita hit no banco a cada mensagem)
chat:session:{session_id} → HASH com contexto atual da conversa

# Rate limiting por sessão
chat:ratelimit:{session_id} → Counter com TTL de 60s

# Rate limiting global (proteger contra abuso)
chat:ratelimit:global → Counter com TTL de 60s

# Lock de geração de plano (evitar duplicatas)
plan:lock:{lead_id} → String com TTL de 300s
```

### Padrão de processamento de mensagem

```
1. Mensagem chega no endpoint
2. Valida rate limit (Redis counter)
3. Se dentro do limite:
   a. Salva mensagem no PostgreSQL
   b. Puxa contexto do Redis (ou monta do banco se cache miss)
   c. Chama Claude API
   d. Salva resposta no PostgreSQL
   e. Atualiza contexto no Redis
   f. Retorna resposta
4. Se Claude API falhar:
   a. Enfileira mensagem no Redis
   b. Retorna "processando..." pro frontend
   c. Worker retry com backoff exponencial
   d. Quando processar, notifica via polling/SSE
```

---

## 7. Segurança e Limites

### Proteção contra abuso
- Rate limit: 3 mensagens/minuto por sessão
- Rate limit global: 100 mensagens/minuto total
- Max sessões simultâneas: 20
- Honeypot field no formulário (anti-bot)
- Validação de email (formato + MX record check)
- Max 500 tokens por mensagem do lead
- Sessão expira em 30 min de inatividade

### Dados e privacidade
- Emails e WhatsApp armazenados com cifragem em repouso
- Logs de conversa retidos por 90 dias, depois anonimizados
- Conformidade LGPD: consentimento explícito no form, opção de exclusão

### Custo estimado por lead
| Item | Custo |
|---|---|
| ~15 mensagens Sonnet (input) | ~$0.02 |
| ~15 respostas Sonnet (output) | ~$0.03 |
| Geração do plano (4K tokens) | ~$0.02 |
| Whisper (se usar áudio) | ~$0.01 |
| **Total por lead** | **~$0.05-0.08** |

Com 100 leads/mês = ~$5-8/mês de API. Margem excelente.

---

## 8. Deploy e Infra

### Docker Compose (Swarm)

```yaml
services:
  api:
    image: mondayplanner-api:latest
    deploy:
      replicas: 2
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
      - MONDAY_API_KEY=${MONDAY_API_KEY}
    networks:
      - traefik-public
      - internal
    labels:
      - traefik.enable=true
      - traefik.http.routers.planner.rule=Host(`planner.seudominio.com`)

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    networks:
      - internal

  db:
    image: postgres:16-alpine
    volumes:
      - pg_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=mondayplanner
    networks:
      - internal

networks:
  traefik-public:
    external: true
  internal:
    driver: overlay

volumes:
  redis_data:
  pg_data:
```

### CI/CD (GitHub Actions)
- Push em `main` → build imagem → deploy no Swarm via SSH
- Migrations automáticas com Alembic
- Health checks no endpoint `/health`

---

## 9. Métricas e KPIs

### Funil
- Taxa de conclusão do form (steps completados / visitas)
- Taxa de conclusão do chat (planos gerados / chats iniciados)
- Taxa de agendamento de call (calls / planos gerados)
- Taxa de conversão (fechamentos / calls)

### Operacionais
- Tempo médio de conversa
- Tokens médios por sessão
- Taxa de erro do agente (respostas fora do escopo)
- NPS do planejamento (pesquisa pós-geração)

---

## 10. Roadmap de Evolução

### v1.0 (MVP) — Foco atual
- Form multi-step + chat texto + geração planejamento.md
- Kanban de leads na Monday
- Deploy no VPS

### v1.5
- Suporte a áudio e imagem no chat
- Upload de arquivos
- Score automático de leads
- Dashboard de métricas (Streamlit ou similar)

### v2.0
- Agendamento de call integrado (Calendly/Cal.com)
- Execução automática do planejamento na Monday via MCP
- Área do cliente para acompanhar implementação
- White-label para outros consultores Monday
