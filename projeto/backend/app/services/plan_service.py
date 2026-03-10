"""
PlanService — geração do planejamento.md via Claude API.

Fluxo:
  1. Carrega Plan (status=generating) + Lead + histórico de mensagens
  2. Lock no Redis (plan:lock:{lead_id}) para evitar geração duplicada
  3. Monta prompt com contexto completo
  4. Chama Claude API (max_tokens 4096)
  5. Extrai SUMMARY_JSON do output
  6. Salva content_md + summary_json no DB (status=generated)
  7. Notifica Make webhook (fire-and-forget)
  8. Em caso de erro: atualiza status=error
"""
import json
import re
import uuid
from typing import Optional

import anthropic
import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.agent.prompts import build_plan_generation_prompt
from app.config import settings
from app.models.chat_message import ChatMessage
from app.models.lead import Lead
from app.models.plan import Plan
from app.utils.redis_client import get_redis

logger = structlog.get_logger()

_PLAN_LOCK_TTL = 300  # 5 minutos
_PLAN_MAX_TOKENS = 4096


def _get_claude_client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=settings.claude_api_key)


def _extract_summary(text: str) -> tuple[str, Optional[dict]]:
    """
    Separa o markdown do JSON de resumo embutido pelo Claude.
    Retorna (content_md limpo, summary_dict ou None).
    """
    pattern = r"\nSUMMARY_JSON:\s*(\{.+\})\s*$"
    match = re.search(pattern, text, re.DOTALL)

    if not match:
        return text.strip(), None

    content_md = text[: match.start()].strip()
    try:
        summary = json.loads(match.group(1))
        return content_md, summary
    except json.JSONDecodeError:
        return content_md, None


async def _build_conversation_history(session_id: uuid.UUID, db: AsyncSession) -> str:
    """Formata o histórico completo da sessão como texto para o prompt."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()

    lines = []
    for msg in messages:
        role_label = "CONSULTOR" if msg.role == "assistant" else "CLIENTE"
        lines.append(f"{role_label}: {msg.content}")

    return "\n\n".join(lines)


async def _notify_make(lead: Lead, plan: Plan) -> None:
    """
    Notifica o webhook do Make com os dados do lead e link do plano.
    Fire-and-forget: erros são logados mas não interrompem o fluxo.
    Make é responsável por:
      - Criar item no pipeline da Monday
      - Enviar email ao lead com o link do plano
    """
    if not settings.make_webhook_url:
        logger.debug("make_webhook_not_configured")
        return

    view_url = f"{settings.api_base_url}/api/v1/plans/{plan.id}/view"
    download_url = f"{settings.api_base_url}/api/v1/plans/{plan.id}/download"

    payload = {
        "lead_id": str(lead.id),
        "empresa": lead.empresa,
        "nome_contato": lead.nome_contato,
        "email": lead.email,
        "whatsapp": lead.whatsapp or "",
        "segmento": lead.segmento,
        "tipo_negocio": lead.tipo_negocio,
        "porte": lead.porte,
        "score": lead.score,
        "areas_interesse": lead.areas_interesse or [],
        "plan_id": str(plan.id),
        "plan_view_url": view_url,
        "plan_download_url": download_url,
        "summary": plan.summary_json or {},
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(settings.make_webhook_url, json=payload)
            resp.raise_for_status()
        logger.info("make_webhook_sent", lead_id=str(lead.id), plan_id=str(plan.id))
    except Exception as exc:
        logger.warning("make_webhook_failed", error=str(exc), lead_id=str(lead.id))


async def generate_plan(plan_id: uuid.UUID, db: AsyncSession) -> None:
    """
    Gera o planejamento.md e salva no banco.
    Usa lock Redis para evitar geração duplicada.
    """
    # Carrega Plan
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        logger.error("plan_not_found", plan_id=str(plan_id))
        return

    # Bind context para logs estruturados
    structlog.contextvars.bind_contextvars(
        plan_id=str(plan_id),
        lead_id=str(plan.lead_id),
    )

    # Lock Redis anti-duplicata
    redis = get_redis()
    lock_key = f"plan:lock:{plan.lead_id}"
    acquired = await redis.set(lock_key, str(plan_id), ex=_PLAN_LOCK_TTL, nx=True)
    if not acquired:
        logger.warning("plan_lock_already_held")
        return

    lead = None
    try:
        # Carrega Lead
        lead_result = await db.execute(select(Lead).where(Lead.id == plan.lead_id))
        lead = lead_result.scalar_one_or_none()
        if not lead:
            raise ValueError(f"Lead {plan.lead_id} não encontrado")

        # Monta histórico da conversa
        conversation_history = ""
        if plan.session_id:
            conversation_history = await _build_conversation_history(plan.session_id, db)

        # Gera o planejamento via Claude
        client = _get_claude_client()
        prompt = build_plan_generation_prompt(lead, conversation_history)

        response = await client.messages.create(
            model=settings.claude_model,
            max_tokens=_PLAN_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        raw_output = response.content[0].text
        content_md, summary = _extract_summary(raw_output)

        # Salva no DB
        plan.content_md = content_md
        plan.summary_json = summary
        plan.status = "generated"
        await db.commit()

        logger.info("plan_generated", content_length=len(content_md))

        # Notifica Make (fire-and-forget, depois do commit)
        await _notify_make(lead, plan)

    except Exception as exc:
        logger.error("plan_generation_failed", error=str(exc))
        plan.status = "error"
        await db.commit()
    finally:
        await redis.delete(lock_key)
        structlog.contextvars.unbind_contextvars("plan_id", "lead_id")


async def generate_plan_background(plan_id: uuid.UUID) -> None:
    """
    Entry point para BackgroundTasks do FastAPI.
    Cria sua própria sessão de DB (a sessão do request já foi fechada).
    """
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with factory() as db:
            await generate_plan(plan_id, db)
    except Exception as exc:
        logger.error("generate_plan_background_failed", plan_id=str(plan_id), error=str(exc))
        # Tenta marcar como erro se possível
        try:
            async with factory() as db:
                result = await db.execute(select(Plan).where(Plan.id == plan_id))
                plan = result.scalar_one_or_none()
                if plan and plan.status == "generating":
                    plan.status = "error"
                    await db.commit()
        except Exception:
            pass
    finally:
        await engine.dispose()


# ── Queries de leitura ────────────────────────────────────────────────────


async def get_plan_status(plan_id: uuid.UUID, db: AsyncSession) -> Optional[Plan]:
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    return result.scalar_one_or_none()


async def get_plan(plan_id: uuid.UUID, db: AsyncSession) -> Optional[Plan]:
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    return result.scalar_one_or_none()
