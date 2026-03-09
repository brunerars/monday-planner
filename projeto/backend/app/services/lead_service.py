import uuid
import json
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.lead import Lead
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
    await db.commit()
    await db.refresh(lead)

    log = logger.bind(lead_id=str(lead.id), empresa=lead.empresa, score=score)
    log.info("lead_created")
    return lead


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


async def create_partial_lead(data: PartialLeadCreate) -> dict:
    redis = get_redis()
    partial_id = str(uuid.uuid4())
    key = f"lead:partial:{partial_id}"
    payload = {"step_completed": data.step_completed, "data": data.data}
    await redis.setex(key, 86400, json.dumps(payload))  # TTL 24h
    logger.info("partial_lead_saved", partial_id=partial_id, step=data.step_completed)
    return {"id": partial_id, "step_completed": data.step_completed, "recoverable": True}
