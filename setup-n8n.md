# Setup n8n — Automações MondayPlanner

## Visão Geral

O n8n é responsável por automações de follow-up e recuperação de leads que abandonaram o formulário. Os dados ficam persistidos no Postgres (tabela `partial_leads`) e no Redis (TTL 24h para recovery em tempo real).

---

## 1. Cron Job: Recuperação de Leads Parciais

### Objetivo
Buscar leads que iniciaram o formulário (step 3+), informaram email, mas **não finalizaram o cadastro**. Disparar follow-up por email.

### Query SQL

```sql
-- Leads parciais que NÃO viraram leads completos nas últimas 24h
SELECT pl.*
FROM partial_leads pl
LEFT JOIN leads l ON LOWER(l.email) = pl.email
WHERE pl.created_at > now() - interval '24 hours'
  AND l.id IS NULL
ORDER BY pl.created_at DESC;
```

### Dados disponíveis no `data` (JSONB)

| Campo | Disponível a partir do step |
|---|---|
| `tipo_negocio` | 1 |
| `segmento` | 1 |
| `empresa` | 1 |
| `porte` | 1 |
| `cidade`, `estado`, `colaboradores` | 2 |
| `email`, `nome_contato`, `whatsapp`, `cargo` | 3 |
| `usa_monday`, `areas_interesse`, `dor_principal` | 4 |

### Workflow n8n sugerido

```
[Cron Trigger: a cada 4h]
    → [Postgres Node: executar query acima]
    → [IF: tem resultados?]
        → [SIM] → [Send Email / WhatsApp]
            - Assunto: "Você não terminou seu planejamento, {nome_contato}!"
            - Corpo: link para retomar o form (email será recuperado automaticamente via /leads/partial/recover)
        → [NÃO] → [No-op]
```

### Conexão com o Postgres

```
Host: db (se n8n estiver na mesma rede Docker) ou localhost:5432
Database: mondayplanner
User: mondayplanner
Password: mondayplanner
SSL: off (dev) / on (prod)
```

---

## 2. Webhook Make: Criação de Lead no CRM

### Fluxo atual
Quando o plano é gerado com sucesso, o backend faz `POST` ao `MAKE_WEBHOOK_URL` com o payload completo do lead + links do plano.

### Payload enviado ao Make

```json
{
  "lead_id": "uuid",
  "empresa": "TechBrasil Soluções Ltda",
  "nome_contato": "Marina Costa",
  "email": "marina@techbrasil.com.br",
  "whatsapp": "41988887777",
  "segmento": "Tecnologia",
  "tipo_negocio": "B2B",
  "porte": "EPP",
  "score": 55,
  "areas_interesse": ["Vendas", "Projetos", "Suporte"],
  "plan_id": "uuid",
  "plan_view_url": "https://api.monday-planner.arvsystems.cloud/api/v1/plans/{id}/view",
  "plan_download_url": "https://api.monday-planner.arvsystems.cloud/api/v1/plans/{id}/download",
  "summary": {
    "boards": 3,
    "automacoes_make": 5,
    "plano_recomendado": "Pro",
    "semanas_estimadas": 4
  }
}
```

### O que o Make faz com isso
1. **Cria item no board de pipeline da Monday.com** (lead como item, campos mapeados)
2. **Envia email ao lead** com link do plano HTML (`plan_view_url`)

### Teste local do payload
```bash
python scripts/test_webhook_payload.py --base-url http://localhost:8000
```

---

## 3. Tabela `partial_leads` — Schema

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | UUID PK | auto-generated |
| `session_token` | VARCHAR(36) | indexed, UUID gerado no momento do save |
| `step_completed` | INTEGER | 1-4, step do form que o lead completou |
| `data` | JSONB | dados parciais do formulário |
| `email` | VARCHAR(200) | nullable, indexed — preenchido a partir do step 3 |
| `created_at` | TIMESTAMPTZ | server_default now() |

**Obs:** Só são persistidos no Postgres os partials com email (step >= 3). Steps 1-2 ficam apenas no Redis para recovery de sessão.

---

## 4. Redis Keys relacionadas

```
lead:partial:{partial_id}     → JSON (TTL 24h) — recovery por ID
lead:partial:email:{email}    → JSON (TTL 24h) — recovery por email (cross-device)
```

---

## 5. Endpoint de Recovery (usado pelo frontend)

```
GET /api/v1/leads/partial/recover?email=xxx
→ 200: { id, step_completed, data }
→ 404: { code: "PARTIAL_NOT_FOUND" }
```

O frontend chama este endpoint quando o usuário completa o step 3 (email validado). Se encontrar dados salvos, oferece a opção de continuar de onde parou.
