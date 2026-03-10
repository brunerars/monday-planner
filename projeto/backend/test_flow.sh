#!/bin/bash
# Script de teste rápido: cria lead → inicia chat → encerra → gera plano
# Uso: bash test_flow.sh [BASE_URL]

BASE="${1:-http://localhost:8000}"
API="$BASE/api/v1"

echo "=== 1. Criando lead ==="
LEAD=$(curl -s -X POST "$API/leads" \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_negocio": "B2B",
    "segmento": "Tecnologia",
    "empresa": "TechNova Solutions",
    "porte": "Medio",
    "colaboradores": "51-200",
    "cidade": "São Paulo",
    "estado": "SP",
    "nome_contato": "Ricardo Mendes",
    "email": "ricardo_teste_'$RANDOM'@technova.com.br",
    "whatsapp": "11999887766",
    "cargo": "Diretor de Operações",
    "usa_monday": "avaliando",
    "areas_interesse": ["Vendas", "Projetos", "Operacoes"],
    "dor_principal": "Processos manuais em planilhas, sem visibilidade de pipeline e projetos atrasados"
  }')

LEAD_ID=$(echo "$LEAD" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null)
if [ -z "$LEAD_ID" ]; then
  echo "ERRO ao criar lead:"
  echo "$LEAD"
  exit 1
fi
echo "Lead ID: $LEAD_ID"

echo ""
echo "=== 2. Iniciando chat ==="
START=$(curl -s -X POST "$API/chat/start" \
  -H "Content-Type: application/json" \
  -d "{\"lead_id\": \"$LEAD_ID\"}")

SESSION_ID=$(echo "$START" | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])" 2>/dev/null)
if [ -z "$SESSION_ID" ]; then
  echo "ERRO ao iniciar chat:"
  echo "$START"
  exit 1
fi
echo "Session ID: $SESSION_ID"
echo "Greeting: $(echo "$START" | python3 -c "import sys,json; print(json.load(sys.stdin)['greeting'][:80])" 2>/dev/null)..."

echo ""
echo "=== 3. Enviando mensagem completa ==="
MSG=$(curl -s -X POST "$API/chat/message" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"content\": \"Deixa eu te dar o contexto completo de uma vez: Somos a TechNova, empresa B2B de tecnologia com 120 colaboradores. Hoje usamos planilhas pra tudo - pipeline de vendas, gestão de projetos e operações. O funil de vendas tem uns 200 leads/mês, ciclo de 45 dias, e a gente perde muito deal por falta de follow-up. Nos projetos, usamos uma mistura de Trello e planilha, mas ninguém sabe o status real. O time de operações faz onboarding de clientes manualmente, com checklist no Google Docs. Nossas dores principais: zero visibilidade do pipeline, projetos atrasam porque dependências não são rastreadas, e o handoff de vendas pra operações é um caos - informação se perde. Já tentamos Asana mas não colou porque era complexo demais. Queremos algo que integre com nosso Gmail e WhatsApp Business. O time todo precisa de acesso, uns 80 usuários ativos. Orçamento não é o principal bloqueio, mas precisa fazer sentido. Pode gerar o planejamento com base nisso.\"
  }")

echo "Response: $(echo "$MSG" | python3 -c "import sys,json; print(json.load(sys.stdin)['response'][:100])" 2>/dev/null)..."
echo "Messages used: $(echo "$MSG" | python3 -c "import sys,json; print(json.load(sys.stdin)['session_status']['messages_used'])" 2>/dev/null)"

echo ""
echo "=== 4. Encerrando sessão e gerando plano ==="
END=$(curl -s -X POST "$API/chat/end" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\", \"reason\": \"test_complete\"}")

PLAN_ID=$(echo "$END" | python3 -c "import sys,json; print(json.load(sys.stdin)['plan_trigger']['poll_url'].split('/')[-1])" 2>/dev/null)
if [ -z "$PLAN_ID" ]; then
  echo "ERRO ao encerrar:"
  echo "$END"
  exit 1
fi
echo "Plan ID: $PLAN_ID"

echo ""
echo "=== 5. Aguardando geração do plano ==="
for i in $(seq 1 20); do
  sleep 3
  STATUS=$(curl -s "$API/plans/status/$PLAN_ID")
  PLAN_STATUS=$(echo "$STATUS" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null)
  echo "  [$i] Status: $PLAN_STATUS"

  if [ "$PLAN_STATUS" = "completed" ]; then
    echo ""
    echo "=== PRONTO ==="
    echo "Ver plano: $BASE/api/v1/plans/$PLAN_ID/view"
    echo "Download:  $BASE/api/v1/plans/$PLAN_ID/download"
    exit 0
  fi

  if [ "$PLAN_STATUS" = "error" ]; then
    echo "ERRO na geração do plano."
    exit 1
  fi
done

echo "Timeout — plano ainda gerando após 60s."
exit 1
