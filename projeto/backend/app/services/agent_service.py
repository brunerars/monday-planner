"""
AgentService — core loop do chat com o agente MondayPlanner.

Fluxo do process_message():
  1. Carrega e valida sessão
  2. Checa rate limit (Redis)
  3. Checa limite de mensagens (guardrails)
  4. Valida tokens do input (guardrails)
  5. Salva mensagem do usuário no DB
  6. Monta contexto (sliding window via ContextManager)
  7. Chama Claude API (retry 2x com backoff)
  8. Salva resposta no DB
  9. Atualiza contador da sessão
 10. Se is_final: cria Plan record (status=generating) e encerra sessão
 11. Retorna resposta
"""
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

import anthropic
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.context import ContextManager
from app.agent.guardrails import GuardrailsChecker
from app.agent.prompts import FINAL_NOTE, PENULTIMATE_NOTE, build_message_counter_note, build_system_prompt
from app.config import settings
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.lead import Lead
from app.models.plan import Plan
from app.utils.rate_limiter import check_session_rate_limit

logger = structlog.get_logger()

_context_manager = ContextManager()
_guardrails = GuardrailsChecker(
    max_input_tokens=settings.agent_max_input_tokens,
    max_messages=settings.agent_max_messages,
)


def _get_claude_client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=settings.claude_api_key)


async def _get_session(db: AsyncSession, session_id: uuid.UUID) -> Optional[ChatSession]:
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    return result.scalar_one_or_none()


async def _get_lead(db: AsyncSession, lead_id: uuid.UUID) -> Optional[Lead]:
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    return result.scalar_one_or_none()


async def _call_claude_with_retry(
    client: anthropic.AsyncAnthropic,
    system: str,
    messages: list[dict],
    max_tokens: int,
    max_retries: int = 2,
) -> str:
    """Chama Claude API com retry exponencial em caso de falha."""
    last_error: Exception = RuntimeError("Sem tentativas")
    for attempt in range(max_retries + 1):
        try:
            response = await client.messages.create(
                model=settings.claude_model,
                system=system,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.3,
            )
            return response.content[0].text
        except (anthropic.RateLimitError, anthropic.APIStatusError) as exc:
            last_error = exc
            if attempt < max_retries:
                await asyncio.sleep(2**attempt)
        except anthropic.APIConnectionError as exc:
            last_error = exc
            if attempt < max_retries:
                await asyncio.sleep(2**attempt)
    raise last_error


# ── Operações públicas ──────────────────────────────────────────────────────


async def start_session(lead_id: uuid.UUID, db: AsyncSession) -> dict:
    """
    Cria sessão de chat e gera greeting personalizado via Claude.
    Raises ValueError com código em caso de erro de negócio.
    """
    lead = await _get_lead(db, lead_id)
    if not lead:
        raise ValueError("LEAD_NOT_FOUND")

    structlog.contextvars.bind_contextvars(lead_id=str(lead_id))

    # Verifica sessão ativa existente
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.lead_id == lead_id, ChatSession.status == "active"
        ).order_by(ChatSession.started_at.desc())
    )
    existing = result.scalars().first()
    if existing:
        raise ValueError(f"SESSION_ACTIVE:{existing.id}")

    # Cria sessão
    session = ChatSession(lead_id=lead_id, status="active")
    db.add(session)
    await db.flush()

    # Gera greeting via Claude
    client = _get_claude_client()
    system_prompt = build_system_prompt(lead)

    greeting = await _call_claude_with_retry(
        client=client,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": "Oi, acabei de preencher o formulário.",
            }
        ],
        max_tokens=settings.agent_max_output_tokens,
    )

    # Salva greeting como primeira mensagem
    msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=greeting,
        content_type="text",
    )
    db.add(msg)
    session.total_messages = 1

    await db.commit()
    await db.refresh(session)

    logger.info("session_started", session_id=str(session.id), lead_id=str(lead_id))

    return {"session": session, "lead": lead, "greeting": greeting}


async def process_message(
    session_id: uuid.UUID, content: str, db: AsyncSession
) -> dict:
    """
    Processa mensagem do usuário e retorna resposta do agente.
    Raises ValueError com código em caso de erro de negócio.
    """
    # 1. Carrega sessão
    session = await _get_session(db, session_id)
    if not session:
        raise ValueError("SESSION_NOT_FOUND")
    if session.status != "active":
        raise ValueError("SESSION_EXPIRED")

    lead = await _get_lead(db, session.lead_id)

    structlog.contextvars.bind_contextvars(
        session_id=str(session_id),
        lead_id=str(session.lead_id),
    )

    # 2. Rate limit
    rate_ok, retry_after = await check_session_rate_limit(str(session_id))
    if not rate_ok:
        raise ValueError(f"RATE_LIMITED:{retry_after}")

    # 3. Limite de mensagens
    limit_status, is_blocked = _guardrails.check_message_limit(session.total_messages)
    if is_blocked:
        raise ValueError("MESSAGE_LIMIT_REACHED")

    # 4. Valida input
    valid, error_msg = _guardrails.validate_input(content)
    if not valid:
        raise ValueError(f"INVALID_INPUT:{error_msg}")

    # 5. Salva mensagem do usuário
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=content,
        content_type="text",
    )
    db.add(user_msg)
    await db.flush()

    # Contagem após a mensagem do usuário (antes do assistant responder)
    messages_after_user = session.total_messages + 1
    # Após o assistant responder será +2
    is_final_exchange = messages_after_user >= settings.agent_max_messages
    is_penultimate_exchange = messages_after_user == settings.agent_max_messages - 1

    # 6. Monta contexto
    client = _get_claude_client()
    system_prompt = build_system_prompt(lead)
    messages = await _context_manager.build_messages(session, lead, db)

    # Adiciona nota de limite à última mensagem do usuário no contexto
    if messages and messages[-1]["role"] == "user":
        if is_final_exchange:
            messages[-1]["content"] += FINAL_NOTE
        elif is_penultimate_exchange:
            messages[-1]["content"] += PENULTIMATE_NOTE
        else:
            counter_note = build_message_counter_note(messages_after_user, settings.agent_max_messages)
            if counter_note:
                messages[-1]["content"] += counter_note

    # 7. Chama Claude API
    response_text = await _call_claude_with_retry(
        client=client,
        system=system_prompt,
        messages=messages,
        max_tokens=settings.agent_max_output_tokens,
    )

    # 8. Salva resposta
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=response_text,
        content_type="text",
    )
    db.add(assistant_msg)

    # 9. Atualiza contador (user + assistant = +2)
    session.total_messages = messages_after_user + 1
    is_final = is_final_exchange or session.total_messages >= settings.agent_max_messages

    # 10. Se final: encerra sessão e cria Plan record
    plan_id: Optional[uuid.UUID] = None
    if is_final:
        session.status = "completed"
        session.ended_at = datetime.now(timezone.utc)

        plan = Plan(
            lead_id=session.lead_id,
            session_id=session.id,
            empresa=lead.empresa,
            content_md="",
            status="generating",
        )
        db.add(plan)
        await db.flush()
        plan_id = plan.id

    await db.commit()

    # Comprime contexto de forma não-bloqueante após finalizar a transação
    if not is_final:
        try:
            await _context_manager.maybe_compress(session, db, client)
        except Exception as exc:
            logger.warning("context_compression_error", error=str(exc))

    logger.info(
        "message_processed",
        session_id=str(session_id),
        messages_used=session.total_messages,
        is_final=is_final,
    )

    return {
        "message_id": assistant_msg.id,
        "response": response_text,
        "messages_used": session.total_messages,
        "is_final": is_final,
        "plan_id": plan_id,
    }


async def end_session(session_id: uuid.UUID, db: AsyncSession) -> dict:
    """Encerra sessão manualmente e cria Plan record para geração."""
    session = await _get_session(db, session_id)
    if not session:
        raise ValueError("SESSION_NOT_FOUND")
    if session.status != "active":
        raise ValueError("SESSION_ALREADY_ENDED")

    lead = await _get_lead(db, session.lead_id)

    session.status = "completed"
    session.ended_at = datetime.now(timezone.utc)

    plan = Plan(
        lead_id=session.lead_id,
        session_id=session.id,
        empresa=lead.empresa,
        content_md="",
        status="generating",
    )
    db.add(plan)
    await db.flush()
    plan_id = plan.id

    await db.commit()

    try:
        await _context_manager.invalidate_cache(session_id)
    except Exception as exc:
        logger.warning("cache_invalidation_error", error=str(exc))

    logger.info("session_ended", session_id=str(session_id), plan_id=str(plan_id))

    return {"session": session, "plan_id": plan_id}


async def get_history(session_id: uuid.UUID, db: AsyncSession) -> dict:
    """Retorna histórico completo de mensagens da sessão."""
    session = await _get_session(db, session_id)
    if not session:
        raise ValueError("SESSION_NOT_FOUND")

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()

    return {"session": session, "messages": list(messages)}
