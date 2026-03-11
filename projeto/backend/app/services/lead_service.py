import uuid
import json
from typing import Optional

import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.lead import Lead
from app.models.partial_lead import PartialLead
from app.schemas.lead import LeadCreate, LeadStatusUpdate, PartialLeadCreate
from app.utils.redis_client import get_redis

logger = structlog.get_logger()

_SCORE_PORTE = {"Grande": 30, "Medio": 20, "EPP": 10, "ME": 5, "MEI": 2}
_SCORE_COLABORADORES = {"500+": 20, "201-500": 15, "51-200": 10, "11-50": 5, "6-10": 3, "1-5": 1}
_STATUS_VALIDOS = {
    "novo", "planejamento_gerado", "call_agendada",
    "proposta_enviada", "fechado_ganho", "fechado_perdido",
}


def calculate_score(data: LeadCreate) -> int:
    score = 0
    score += 20 if data.tipo_negocio == "B2B" else 10
    score += _SCORE_PORTE.get(data.porte, 0)
    if data.colaboradores:
        score += _SCORE_COLABORADORES.get(data.colaboradores, 0)
    score += len(data.areas_interesse) * 5
    if data.usa_monday == "sim":
        score += 10
    elif data.usa_monday == "avaliando":
        score += 5
    if data.dor_principal:
        score += 5
    return score


def calculate_score_breakdown(lead: Lead) -> dict:
    """Retorna o breakdown detalhado do score para inclusão no payload Make."""
    breakdown = {}
    breakdown["tipo_negocio"] = {"valor": lead.tipo_negocio, "pontos": 20 if lead.tipo_negocio == "B2B" else 10}
    breakdown["porte"] = {"valor": lead.porte, "pontos": _SCORE_PORTE.get(lead.porte, 0)}
    if lead.colaboradores:
        breakdown["colaboradores"] = {"valor": lead.colaboradores, "pontos": _SCORE_COLABORADORES.get(lead.colaboradores, 0)}
    areas = lead.areas_interesse or []
    breakdown["areas_interesse"] = {"valor": areas, "pontos": len(areas) * 5}
    if lead.usa_monday:
        pontos = 10 if lead.usa_monday == "sim" else (5 if lead.usa_monday == "avaliando" else 0)
        breakdown["usa_monday"] = {"valor": lead.usa_monday, "pontos": pontos}
    breakdown["dor_principal"] = {"valor": bool(lead.dor_principal), "pontos": 5 if lead.dor_principal else 0}
    breakdown["total"] = lead.score
    return breakdown


async def create_lead(db: AsyncSession, data: LeadCreate) -> Lead:
    result = await db.execute(select(Lead).where(Lead.email == data.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "LEAD_EXISTS",
                "message": "Já existe um registro com este e-mail",
                "lead_id": str(existing.id),
            },
        )

    score = calculate_score(data)
    lead = Lead(
        **data.model_dump(exclude={"areas_interesse"}),
        areas_interesse=data.areas_interesse,
        score=score,
    )
    db.add(lead)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # Race condition: email inserido entre o SELECT e o INSERT
        result = await db.execute(select(Lead).where(Lead.email == data.email))
        existing = result.scalar_one_or_none()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "LEAD_EXISTS",
                "message": "Já existe um registro com este e-mail",
                "lead_id": str(existing.id) if existing else None,
            },
        )
    await db.refresh(lead)

    log = logger.bind(lead_id=str(lead.id), empresa=lead.empresa, score=score)
    log.info("lead_created")
    return lead


async def get_all_leads(db: AsyncSession) -> list[Lead]:
    result = await db.execute(select(Lead).order_by(Lead.created_at.desc()))
    return list(result.scalars().all())


async def get_lead(db: AsyncSession, lead_id: uuid.UUID) -> Lead:
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "LEAD_NOT_FOUND", "message": "Lead não encontrado"},
        )
    return lead


async def update_lead_status(
    db: AsyncSession, lead_id: uuid.UUID, data: LeadStatusUpdate
) -> Lead:
    if data.status not in _STATUS_VALIDOS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_STATUS",
                "message": f"Status inválido. Válidos: {sorted(_STATUS_VALIDOS)}",
            },
        )
    lead = await get_lead(db, lead_id)
    lead.status = data.status
    await db.commit()
    await db.refresh(lead)
    logger.bind(lead_id=str(lead_id), new_status=data.status).info("lead_status_updated")
    return lead


async def create_partial_lead(data: PartialLeadCreate, db: Optional[AsyncSession] = None) -> dict:
    redis = get_redis()
    partial_id = str(uuid.uuid4())
    key = f"lead:partial:{partial_id}"
    payload = {"id": partial_id, "step_completed": data.step_completed, "data": data.data}
    payload_json = json.dumps(payload)
    await redis.setex(key, 86400, payload_json)  # TTL 24h

    # Índice por email para recovery cross-device
    email = data.data.get("email")
    if email and isinstance(email, str) and email.strip():
        normalized_email = email.strip().lower()
        email_key = f"lead:partial:email:{normalized_email}"
        await redis.setex(email_key, 86400, payload_json)

        # Persistir no Postgres (durável para automações n8n)
        if db:
            partial = PartialLead(
                session_token=partial_id,
                step_completed=data.step_completed,
                data=data.data,
                email=normalized_email,
            )
            db.add(partial)
            await db.commit()

    logger.info("partial_lead_saved", partial_id=partial_id, step=data.step_completed)
    return {"id": partial_id, "step_completed": data.step_completed, "recoverable": True}


async def recover_partial_lead(email: str) -> Optional[dict]:
    redis = get_redis()
    email_key = f"lead:partial:email:{email.strip().lower()}"
    raw = await redis.get(email_key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None
