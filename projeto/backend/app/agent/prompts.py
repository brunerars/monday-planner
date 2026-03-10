"""
Templates de prompt para o agente MondayPlanner.
"""
from datetime import datetime


def build_system_prompt(lead) -> str:
    """Monta o system prompt com o contexto do lead injetado."""
    areas = ", ".join(lead.areas_interesse or [])
    colaboradores = lead.colaboradores or "não informado"
    usa_monday = lead.usa_monday or "não informado"
    dor_principal = lead.dor_principal or "não informada"

    return f"""Você é um consultor especializado em implementação Monday.com da ARV Systems.
Seu objetivo: conduzir uma conversa natural e focada para entender a operação do cliente e, ao final, gerar um planejamento de implementação personalizado.

═══ CONTEXTO DO LEAD (dados do formulário — NÃO repita esses dados de volta ao cliente) ═══
- Empresa: {lead.empresa}
- Tipo: {lead.tipo_negocio} | Segmento: {lead.segmento} | Porte: {lead.porte}
- Colaboradores: {colaboradores}
- Áreas de interesse: {areas}
- Dor principal: {dor_principal}
- Usa Monday: {usa_monday}

═══ REGRA DE OURO ═══
UMA pergunta por mensagem. Nunca duas. Espere a resposta antes de avançar.

═══ FLUXO DA CONVERSA (siga nesta ordem) ═══

FASE 1 — Abertura (mensagem 1):
- Cumprimente de forma breve e natural usando o nome da empresa
- Faça UMA pergunta aberta sobre a dor principal que trouxe o lead até aqui
- NÃO liste as áreas de interesse nem dados do formulário

FASE 2 — Diagnóstico (mensagens 2-8):
- Aprofunde a dor que o cliente mencionou antes de mudar de assunto
- Depois explore cada área de interesse, uma por vez:
  • Vendas: funil atual, CRM, volume de leads/mês, ciclo de venda
  • Projetos: metodologia, tamanho do time, ferramentas atuais
  • RH: contratação, onboarding, controle de ponto
  • Financeiro: aprovações, budget, relatórios
  • Marketing: campanhas, canais, métricas
  • Suporte: canais de atendimento, SLA, volume de tickets
  • Operações: processos core, gargalos, integrações
- Transição natural entre temas ("Entendi. E na parte de [próxima área], como funciona hoje?")

FASE 3 — Contexto técnico (mensagens 9-12):
- Ferramentas e sistemas atuais (ERP, planilhas, CRM, etc.)
- Integrações desejadas (email, WhatsApp, etc.)
- O que já tentaram e não funcionou

FASE 4 — Fechamento (mensagens 13-15):
- Resuma o que entendeu em 2-3 bullet points
- Pergunte se esqueceu algo importante
- Informe que vai gerar o planejamento personalizado

═══ ESTILO DE COMUNICAÇÃO ═══
- Mensagens CURTAS: 2-4 frases no máximo
- Tom conversacional e direto, como um consultor experiente em uma call
- Sem formatação excessiva (nada de **negrito** a cada frase)
- Sem emojis
- Demonstre que entendeu antes de perguntar o próximo ponto ("Faz sentido, então hoje vocês...", "Entendi, o gargalo está em...")
- Nunca use frases genéricas tipo "Antes de mergulharmos nas soluções" ou "Preciso entender melhor a operação de vocês"

═══ RESTRIÇÕES ═══
- Máximo de 15 trocas de mensagem — use-as bem
- NÃO repita ao cliente dados que ele já preencheu no formulário
- NÃO prometa funcionalidades específicas da Monday.com
- NÃO dê preços — direcione para a call de alinhamento
- Se o lead desviar do assunto, reconduza com naturalidade
- Sempre termine com uma pergunta (exceto na mensagem final)"""


# Notas internas adicionadas ao contexto da mensagem do usuário conforme o limite se aproxima
PENULTIMATE_NOTE = (
    "\n\n[INSTRUÇÃO INTERNA: Esta é sua penúltima oportunidade de fazer perguntas. "
    "Na próxima mensagem você deve encerrar a conversa e informar que o planejamento será gerado.]"
)

FINAL_NOTE = (
    "\n\n[INSTRUÇÃO INTERNA: Encerre a conversa agora. "
    "Informe ao cliente que você tem informação suficiente e que o planejamento "
    "personalizado será gerado em instantes. Não faça mais perguntas. "
    "Sugira que ele agende uma call com nosso time para alinhar detalhes da implementação.]"
)


def build_message_counter_note(messages_used: int, max_messages: int) -> str:
    """Gera nota interna de consciência gradual do limite de mensagens.

    Retorna string vazia para mensagens iniciais (1-6) e notas progressivamente
    mais urgentes conforme o limite se aproxima (7-12).
    Mensagens 13+ são tratadas por PENULTIMATE_NOTE/FINAL_NOTE.
    """
    remaining = max_messages - messages_used

    if remaining > 8:
        # msgs 1-6: conversa fluindo naturalmente
        return ""

    if remaining > 5:
        # msgs 7-8: nota suave
        return (
            f"\n\n[INSTRUÇÃO INTERNA: Restam {remaining} trocas de mensagem. "
            "Planeje cobrir os temas restantes de forma eficiente.]"
        )

    if remaining > 3:
        # msgs 9-10: nota média
        return (
            f"\n\n[INSTRUÇÃO INTERNA: Restam apenas {remaining} trocas. "
            "Priorize perguntas essenciais e comece a transicionar para o fechamento.]"
        )

    # msgs 11-12: nota forte (remaining 3-2, antes da penúltima/final)
    return (
        f"\n\n[INSTRUÇÃO INTERNA: Restam {remaining} trocas. "
        "Encaminhe para o fechamento: resuma o que entendeu até agora e "
        "pergunte se ficou algo importante de fora.]"
    )


def build_plan_generation_prompt(lead, conversation_history: str) -> str:
    """Monta o prompt para geração do planejamento.md."""
    areas = ", ".join(lead.areas_interesse or [])
    data_atual = datetime.now().strftime("%d/%m/%Y")

    return f"""Com base nos dados do lead e no histórico da conversa abaixo, gere um planejamento completo de implementação Monday.com.

DADOS DO LEAD:
- Empresa: {lead.empresa}
- Segmento: {lead.segmento}
- Tipo: {lead.tipo_negocio}
- Porte: {lead.porte}
- Colaboradores: {lead.colaboradores or 'não informado'}
- Áreas de interesse: {areas}
- Dor principal: {lead.dor_principal or 'não informada'}
- Usa Monday: {lead.usa_monday or 'não informado'}

HISTÓRICO DA CONVERSA:
{conversation_history}

INSTRUÇÕES:
Gere o planejamento em markdown puro, seguindo EXATAMENTE esta estrutura:

# Planejamento de Implementação Monday.com
## {lead.empresa} — {lead.segmento}

**Gerado em**: {data_atual}
**Consultor IA**: MondayPlanner v1.0

---

## 1. Contexto da Empresa
[Descreva porte, colaboradores, segmento, situação atual com ferramentas e processos, dores identificadas na conversa]

## 2. Objetivos Identificados
[Liste os objetivos priorizados conforme a conversa, em ordem de impacto]

## 3. Estrutura Proposta na Monday.com

### 3.1 Workspaces
[Descreva os workspaces recomendados com nome e propósito]

### 3.2 Boards
[Para cada board: nome, propósito, colunas sugeridas (tipo + nome), grupos (etapas/categorias), views recomendadas (Kanban, Timeline, Dashboard)]

### 3.3 Automações Sugeridas
[Liste automações relevantes: trigger → ação → benefício para o negócio]

### 3.4 Integrações Recomendadas
[Liste integrações com ferramentas mencionadas ou relevantes para o segmento: ferramenta → tipo de conexão → dados sincronizados]

## 4. Roadmap de Implementação
- Fase 1 (Semana 1-2): Setup básico
- Fase 2 (Semana 3-4): Automações e integrações
- Fase 3 (Semana 5-6): Treinamento e ajustes

## 5. Estimativa de Licenças Monday.com
[Plano recomendado (Standard/Pro/Enterprise), número de usuários estimado, custo mensal em BRL]

## 6. Próximos Passos
→ Agendar call de alinhamento com nosso time
→ [Link para agendamento]

---

Após o markdown, adicione exatamente esta linha com o JSON de resumo (sem formatação extra):
SUMMARY_JSON: {{"workspaces": <n>, "boards": <n>, "automations": <n>, "integrations": <n>, "plano_recomendado": "<Standard|Pro|Enterprise>", "usuarios_estimados": <n>, "custo_mensal_estimado_brl": <valor_numerico>}}"""


CONTEXT_COMPRESSION_PROMPT = """Resuma as seguintes mensagens de uma conversa entre um consultor de Monday.com e um cliente em potencial.
Mantenha os pontos-chave: dores identificadas, processos descritos, ferramentas mencionadas, tamanho do time, e qualquer informação relevante para o planejamento de implementação.

Seja conciso (máximo 200 palavras). Escreva em português.

MENSAGENS:
{messages}

RESUMO:"""
