# MondayPlanner — API Contracts v1.0

Base URL: `https://planner.seudominio.com/api/v1`
Content-Type: `application/json`
Autenticação: Pública (leads) / API Key interna (webhooks)

---

## 1. Leads

### POST /leads — Criar lead (form submit)

**Request:**
```json
{
  "tipo_negocio": "B2B",                          // enum: "B2B" | "B2C"
  "segmento": "Tecnologia",                       // string, max 100
  "empresa": "Acme Ltda",                         // string, max 200
  "porte": "ME",                                  // enum: "MEI" | "ME" | "EPP" | "Medio" | "Grande"
  "colaboradores": "11-50",                        // enum: "1-5" | "6-10" | "11-50" | "51-200" | "201-500" | "500+"
  "cidade": "São Paulo",                           // string, max 100
  "estado": "SP",                                  // string, 2 chars
  "nome_contato": "João Silva",                    // string, max 200
  "email": "joao@acme.com.br",                    // string, email válido
  "whatsapp": "11999999999",                       // string, opcional, max 20
  "cargo": "Diretor de Operações",                 // string, max 100
  "usa_monday": "avaliando",                       // enum: "sim" | "nao" | "avaliando"
  "areas_interesse": ["Vendas", "Projetos"],       // array de strings, min 1
  "dor_principal": "Processos manuais em planilha" // string, max 280
}
```

**Response 201:**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "empresa": "Acme Ltda",
  "nome_contato": "João Silva",
  "status": "novo",
  "created_at": "2026-03-08T14:30:00Z"
}
```

**Response 409** (email já existe):
```json
{
  "detail": {
    "code": "LEAD_EXISTS",
    "message": "Já existe um registro com este e-mail",
    "lead_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }
}
```

**Response 422** (validação):
```json
{
  "detail": {
    "code": "VALIDATION_ERROR",
    "errors": [
      {"field": "email", "message": "Formato de e-mail inválido"},
      {"field": "areas_interesse", "message": "Selecione ao menos uma área"}
    ]
  }
}
```

### POST /leads/partial — Salvar form parcial (abandono)

**Request:**
```json
{
  "step_completed": 2,
  "data": {
    "tipo_negocio": "B2B",
    "segmento": "Tecnologia",
    "empresa": "Acme Ltda",
    "porte": "ME"
  }
}
```

**Response 201:**
```json
{
  "id": "partial-uuid-here",
  "step_completed": 2,
  "recoverable": true
}
```

---

## 2. Chat

### POST /chat/start — Iniciar sessão de chat

**Request:**
```json
{
  "lead_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Response 201:**
```json
{
  "session_id": "s1e2s3s4-i5o6-n7id-here-123456789abc",
  "lead_name": "João",
  "lead_empresa": "Acme Ltda",
  "greeting": "Olá João! Vi que a Acme está buscando organizar as áreas de Vendas e Projetos na Monday.com. Você mencionou que a maior dor hoje são processos manuais em planilha — pode me contar um pouco mais sobre como funciona hoje?",
  "config": {
    "max_messages": 15,
    "supports_audio": false,
    "supports_image": false,
    "supports_file": false,
    "session_timeout_minutes": 30
  }
}
```

**Response 404** (lead não encontrado):
```json
{
  "detail": {
    "code": "LEAD_NOT_FOUND",
    "message": "Lead não encontrado"
  }
}
```

**Response 409** (sessão já ativa):
```json
{
  "detail": {
    "code": "SESSION_ACTIVE",
    "message": "Já existe uma sessão ativa para este lead",
    "session_id": "existing-session-uuid"
  }
}
```

### POST /chat/message — Enviar mensagem de texto

**Request:**
```json
{
  "session_id": "s1e2s3s4-i5o6-n7id-here-123456789abc",
  "content": "Hoje a gente controla tudo no Excel, cada vendedor tem sua planilha..."
}
```

**Response 200:**
```json
{
  "message_id": "msg-uuid-here",
  "response": "Entendo. Então cada vendedor tem sua própria planilha e não existe uma visão centralizada do funil. Duas perguntas rápidas:\n\n- Quantos vendedores estão no time hoje?\n- Vocês têm algum processo definido de etapas de venda (tipo lead → proposta → fechamento) ou cada um faz do seu jeito?",
  "session_status": {
    "messages_used": 3,
    "messages_remaining": 12,
    "is_final": false
  }
}
```

**Response 200** (mensagem final — limit atingido ou agente encerrou):
```json
{
  "message_id": "msg-uuid-here",
  "response": "Perfeito, João! Agora tenho uma visão bem clara da operação da Acme. Vou gerar seu planejamento personalizado de implementação Monday.com. Você recebe ele em instantes.",
  "session_status": {
    "messages_used": 15,
    "messages_remaining": 0,
    "is_final": true
  },
  "plan_trigger": {
    "status": "generating",
    "estimated_seconds": 15,
    "poll_url": "/api/v1/plans/status/plan-uuid-here"
  }
}
```

**Response 429** (rate limit):
```json
{
  "detail": {
    "code": "RATE_LIMITED",
    "message": "Aguarde alguns segundos antes de enviar outra mensagem",
    "retry_after_seconds": 20
  }
}
```

**Response 410** (sessão expirada):
```json
{
  "detail": {
    "code": "SESSION_EXPIRED",
    "message": "Sua sessão expirou por inatividade",
    "partial_plan_available": true,
    "plan_url": "/api/v1/plans/plan-uuid-here"
  }
}
```

### POST /chat/upload — Enviar mídia (v1.5)

**Request:** `multipart/form-data`
```
session_id: "s1e2s3s4-i5o6-n7id-here-123456789abc"
file: <binary>
type: "audio" | "image" | "document"
```

**Response 200:**
```json
{
  "message_id": "msg-uuid-here",
  "file_processed": {
    "type": "audio",
    "transcription": "A gente usa o Pipedrive hoje mas ninguém atualiza...",
    "duration_seconds": 23
  },
  "response": "Interessante que vocês já usam o Pipedrive. O que faz o time não atualizar? É questão de interface, processo, ou falta de cobrança da gestão?",
  "session_status": {
    "messages_used": 7,
    "messages_remaining": 8,
    "is_final": false
  }
}
```

**Limites de upload:**
```
audio:    max 60s, formatos: webm, mp3, wav, max 5MB
image:    max 3 por sessão, formatos: jpg, png, webp, max 2MB
document: max 1 por sessão, formatos: xlsx, csv, pdf, max 5MB
```

**Response 413** (arquivo grande demais):
```json
{
  "detail": {
    "code": "FILE_TOO_LARGE",
    "message": "Arquivo excede o limite de 5MB",
    "max_size_mb": 5
  }
}
```

### GET /chat/history/{session_id} — Histórico da sessão

**Response 200:**
```json
{
  "session_id": "s1e2s3s4-i5o6-n7id-here-123456789abc",
  "lead_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "started_at": "2026-03-08T14:30:00Z",
  "ended_at": "2026-03-08T14:42:00Z",
  "total_messages": 12,
  "messages": [
    {
      "id": "msg-uuid-1",
      "role": "assistant",
      "content": "Olá João! Vi que a Acme está buscando...",
      "content_type": "text",
      "created_at": "2026-03-08T14:30:01Z"
    },
    {
      "id": "msg-uuid-2",
      "role": "user",
      "content": "Hoje a gente controla tudo no Excel...",
      "content_type": "text",
      "created_at": "2026-03-08T14:31:15Z"
    }
  ]
}
```

### POST /chat/end — Encerrar sessão manualmente

**Request:**
```json
{
  "session_id": "s1e2s3s4-i5o6-n7id-here-123456789abc",
  "reason": "user_requested"
}
```

**Response 200:**
```json
{
  "session_id": "s1e2s3s4-i5o6-n7id-here-123456789abc",
  "status": "completed",
  "plan_trigger": {
    "status": "generating",
    "estimated_seconds": 15,
    "poll_url": "/api/v1/plans/status/plan-uuid-here"
  }
}
```

---

## 3. Planejamento

### GET /plans/status/{plan_id} — Polling de status da geração

**Response 200** (gerando):
```json
{
  "plan_id": "plan-uuid-here",
  "status": "generating",
  "progress_percent": 60,
  "estimated_seconds_remaining": 8
}
```

**Response 200** (pronto):
```json
{
  "plan_id": "plan-uuid-here",
  "status": "completed",
  "plan_url": "/api/v1/plans/plan-uuid-here",
  "download_url": "/api/v1/plans/plan-uuid-here/download"
}
```

**Response 200** (erro):
```json
{
  "plan_id": "plan-uuid-here",
  "status": "error",
  "message": "Erro ao gerar planejamento. Nosso time foi notificado."
}
```

### GET /plans/{plan_id} — Buscar planejamento

**Response 200:**
```json
{
  "id": "plan-uuid-here",
  "lead_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "empresa": "Acme Ltda",
  "version": 1,
  "status": "generated",
  "content_md": "# Planejamento de Implementação Monday.com\n## Acme Ltda — Tecnologia\n\n...",
  "summary": {
    "workspaces": 1,
    "boards": 3,
    "automations": 5,
    "integrations": 2,
    "plano_recomendado": "Pro",
    "usuarios_estimados": 12,
    "custo_mensal_estimado_brl": 960
  },
  "created_at": "2026-03-08T14:42:15Z",
  "download_url": "/api/v1/plans/plan-uuid-here/download",
  "cta_url": "https://calendly.com/seulink/mondayplanner"
}
```

### GET /plans/{plan_id}/download — Download do .md

**Response 200:**
```
Content-Type: text/markdown
Content-Disposition: attachment; filename="planejamento-acme-ltda.md"

# Planejamento de Implementação Monday.com
## Acme Ltda — Tecnologia
...
```

---

## 4. Webhooks

### POST /webhooks/monday — Receber updates da Monday

**Headers:**
```
X-Monday-Signature: {hmac_signature}
X-API-Key: {internal_api_key}
```

**Request (status changed):**
```json
{
  "event": "status_changed",
  "board_id": 1234567890,
  "item_id": 9876543210,
  "column_id": "status",
  "previous_value": "Planejamento Gerado",
  "new_value": "Call Agendada",
  "timestamp": "2026-03-08T16:00:00Z"
}
```

**Response 200:**
```json
{
  "received": true,
  "action_taken": "lead_status_updated"
}
```

---

## 5. Health

### GET /health

**Response 200:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "redis": "connected",
    "claude_api": "reachable",
    "monday_api": "reachable"
  },
  "uptime_seconds": 86400
}
```

---

## 6. Enums e Constantes (referência frontend)

```typescript
// Para tipagem no frontend

type TipoNegocio = "B2B" | "B2C";

type Porte = "MEI" | "ME" | "EPP" | "Medio" | "Grande";

type Colaboradores = "1-5" | "6-10" | "11-50" | "51-200" | "201-500" | "500+";

type UsaMonday = "sim" | "nao" | "avaliando";

type AreaInteresse =
  | "Vendas"
  | "Projetos"
  | "RH"
  | "Financeiro"
  | "Marketing"
  | "Suporte"
  | "Operacoes";

type SessionStatus = "active" | "completed" | "expired" | "error";

type PlanStatus = "generating" | "completed" | "error";

type LeadStatus =
  | "novo"
  | "planejamento_gerado"
  | "call_agendada"
  | "proposta_enviada"
  | "fechado_ganho"
  | "fechado_perdido";

// Error response pattern
interface ApiError {
  detail: {
    code: string;
    message: string;
    errors?: Array<{ field: string; message: string }>;
    [key: string]: any;
  };
}

// Estados brasileiros para dropdown
type Estado =
  | "AC" | "AL" | "AP" | "AM" | "BA" | "CE" | "DF" | "ES"
  | "GO" | "MA" | "MT" | "MS" | "MG" | "PA" | "PB" | "PR"
  | "PE" | "PI" | "RJ" | "RN" | "RS" | "RO" | "RR" | "SC"
  | "SP" | "SE" | "TO";
```

---

## 7. Notas de Implementação Frontend

### Chat — Padrão de comunicação
O chat usa **polling simples** (não WebSocket) no MVP. O frontend:
1. Envia POST /chat/message
2. Mostra indicador "digitando..." enquanto aguarda response
3. Renderiza resposta quando recebe 200
4. Se receber `is_final: true`, mostra tela de geração do plano
5. Inicia polling no /plans/status/{id} a cada 3s até `completed`

### Chat — Estados da interface
```
IDLE          → Input habilitado, aguardando digitação
SENDING       → Input desabilitado, "digitando..." visível
RATE_LIMITED  → Input desabilitado, countdown visível (retry_after_seconds)
GENERATING    → Chat encerrado, progress bar do plano visível
PLAN_READY    → Plano visível com botões: Download + Agendar Call
SESSION_ERROR → Mensagem de erro + botão "Tentar novamente"
EXPIRED       → Mensagem de expiração + link pro plano parcial (se houver)
```

### Form — Persistência parcial
A cada step completado, o frontend faz POST /leads/partial em background. Se o lead fechar e voltar (via cookie/localStorage com o partial_id), pode retomar de onde parou.

### CORS
O backend aceita origins configuráveis via env var:
```
CORS_ORIGINS=https://seudominio.com,https://www.seudominio.com
```
