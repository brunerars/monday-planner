"""
Chat router — endpoints de conversação com o agente MondayPlanner.

POST /chat/start       → inicia sessão, retorna greeting personalizado
POST /chat/message     → processa mensagem, retorna resposta do agente
POST /chat/end         → encerra sessão manualmente, dispara geração de plano
GET  /chat/history/{id} → histórico completo de mensagens
"""
import uuid

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.agent_service as agent_service
import app.services.plan_service as plan_service

logger = structlog.get_logger()
from app.config import settings
from app.dependencies import get_db
from app.schemas.chat import (
    ChatEndRequest,
    ChatEndResponse,
    ChatHistoryResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatStartRequest,
    ChatStartResponse,
    ChatConfig,
    MessageItem,
    PlanTrigger,
    SessionStatus,
)

router = APIRouter()


def _plan_trigger(plan_id: uuid.UUID) -> PlanTrigger:
    return PlanTrigger(
        status="generating",
        estimated_seconds=15,
        poll_url=f"/api/v1/plans/status/{plan_id}",
    )


# ── POST /chat/start ──────────────────────────────────────────────────────


@router.post(
    "/chat/start",
    response_model=ChatStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Iniciar sessão de chat",
)
async def start_chat(
    data: ChatStartRequest,
    db: AsyncSession = Depends(get_db),
):
    """Cria sessão de chat e retorna greeting personalizado gerado pelo agente."""
    try:
        result = await agent_service.start_session(data.lead_id, db)
    except ValueError as exc:
        code = str(exc)
        if code == "LEAD_NOT_FOUND":
            raise HTTPException(
                status_code=404,
                detail={"code": "LEAD_NOT_FOUND", "message": "Lead não encontrado"},
            )
        if code.startswith("SESSION_ACTIVE:"):
            existing_id = code.split(":", 1)[1]
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "SESSION_ACTIVE",
                    "message": "Já existe uma sessão ativa para este lead",
                    "session_id": existing_id,
                },
            )
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR", "message": code})

    session = result["session"]
    lead = result["lead"]

    return ChatStartResponse(
        session_id=session.id,
        lead_name=lead.nome_contato,
        lead_empresa=lead.empresa,
        greeting=result["greeting"],
        config=ChatConfig(
            max_messages=settings.agent_max_messages,
            supports_audio=False,
            supports_image=False,
            supports_file=False,
            session_timeout_minutes=settings.agent_session_timeout_minutes,
            cta_calendly_url=settings.cta_calendly_url,
        ),
    )


# ── POST /chat/message ────────────────────────────────────────────────────


@router.post(
    "/chat/message",
    response_model=ChatMessageResponse,
    summary="Enviar mensagem de texto",
)
async def send_message(
    data: ChatMessageRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Processa uma mensagem do usuário e retorna a resposta do agente.
    Se is_final=True, dispara a geração do planejamento em background.
    """
    try:
        result = await agent_service.process_message(data.session_id, data.content, db)
    except ValueError as exc:
        code = str(exc)
        if code == "SESSION_NOT_FOUND":
            raise HTTPException(
                status_code=404,
                detail={"code": "SESSION_NOT_FOUND", "message": "Sessão não encontrada"},
            )
        if code == "SESSION_EXPIRED":
            raise HTTPException(
                status_code=410,
                detail={
                    "code": "SESSION_EXPIRED",
                    "message": "Sua sessão expirou por inatividade",
                    "partial_plan_available": False,
                },
            )
        if code.startswith("RATE_LIMITED:"):
            retry_after = int(code.split(":", 1)[1])
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "RATE_LIMITED",
                    "message": "Aguarde alguns segundos antes de enviar outra mensagem",
                    "retry_after_seconds": retry_after,
                },
            )
        if code == "MESSAGE_LIMIT_REACHED":
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "MESSAGE_LIMIT_REACHED",
                    "message": "Limite de mensagens da sessão atingido",
                },
            )
        if code.startswith("INVALID_INPUT:"):
            raise HTTPException(
                status_code=422,
                detail={"code": "INVALID_INPUT", "message": code.split(":", 1)[1]},
            )
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR", "message": code})

    messages_used = result["messages_used"]
    is_final = result["is_final"]
    plan_id = result.get("plan_id")

    # Dispara geração do plano em background quando a sessão finaliza
    if is_final and plan_id:
        background_tasks.add_task(
            plan_service.generate_plan_background,
            plan_id=plan_id,
        )

    trigger = _plan_trigger(plan_id) if is_final and plan_id else None

    return ChatMessageResponse(
        message_id=result["message_id"],
        response=result["response"],
        session_status=SessionStatus(
            messages_used=messages_used,
            messages_remaining=max(0, settings.agent_max_messages - messages_used),
            is_final=is_final,
        ),
        plan_trigger=trigger,
    )


# ── POST /chat/end ────────────────────────────────────────────────────────


@router.post(
    "/chat/end",
    response_model=ChatEndResponse,
    summary="Encerrar sessão manualmente",
)
async def end_chat(
    data: ChatEndRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Encerra a sessão e dispara a geração do planejamento."""
    try:
        result = await agent_service.end_session(data.session_id, db)
    except ValueError as exc:
        code = str(exc)
        if code == "SESSION_NOT_FOUND":
            raise HTTPException(
                status_code=404,
                detail={"code": "SESSION_NOT_FOUND", "message": "Sessão não encontrada"},
            )
        if code == "SESSION_ALREADY_ENDED":
            raise HTTPException(
                status_code=409,
                detail={"code": "SESSION_ALREADY_ENDED", "message": "Sessão já encerrada"},
            )
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR", "message": code})
    except Exception as exc:
        logger.error("end_session_unexpected_error", error=str(exc), session_id=str(data.session_id))
        raise HTTPException(
            status_code=500,
            detail={"code": "INTERNAL_ERROR", "message": "Erro ao encerrar sessão"},
        )

    plan_id = result["plan_id"]
    background_tasks.add_task(
        plan_service.generate_plan_background,
        plan_id=plan_id,
    )

    return ChatEndResponse(
        session_id=result["session"].id,
        status="completed",
        plan_trigger=_plan_trigger(plan_id),
    )


# ── GET /chat/history/{session_id} ────────────────────────────────────────


@router.get(
    "/chat/history/{session_id}",
    response_model=ChatHistoryResponse,
    summary="Histórico de mensagens da sessão",
)
async def get_history(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retorna todas as mensagens de uma sessão de chat."""
    try:
        result = await agent_service.get_history(session_id, db)
    except ValueError as exc:
        if str(exc) == "SESSION_NOT_FOUND":
            raise HTTPException(
                status_code=404,
                detail={"code": "SESSION_NOT_FOUND", "message": "Sessão não encontrada"},
            )
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR"})

    session = result["session"]
    messages = result["messages"]

    return ChatHistoryResponse(
        session_id=session.id,
        lead_id=session.lead_id,
        status=session.status,
        started_at=session.started_at,
        ended_at=session.ended_at,
        total_messages=session.total_messages,
        messages=[
            MessageItem(
                id=m.id,
                role=m.role,
                content=m.content,
                content_type=m.content_type,
                created_at=m.created_at,
            )
            for m in messages
        ],
    )
