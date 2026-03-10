import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.lead import (
    LeadCreate, LeadResponse, LeadDetail,
    LeadStatusUpdate, PartialLeadCreate, PartialLeadResponse,
)
from app.services import lead_service

router = APIRouter()


@router.post(
    "/leads",
    response_model=LeadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar lead (form submit)",
)
async def create_lead(data: LeadCreate, db: AsyncSession = Depends(get_db)):
    """Registra um novo lead a partir do multi-step form."""
    lead = await lead_service.create_lead(db, data)
    return lead


@router.post(
    "/leads/partial",
    response_model=PartialLeadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Salvar form parcial (abandono)",
)
async def create_partial_lead(data: PartialLeadCreate):
    """Persiste dados parciais do form para recuperação posterior."""
    return await lead_service.create_partial_lead(data)


@router.get(
    "/leads",
    response_model=list[LeadResponse],
    summary="Listar todos os leads",
)
async def list_leads(db: AsyncSession = Depends(get_db)):
    return await lead_service.get_all_leads(db)


@router.get(
    "/leads/{lead_id}",
    response_model=LeadDetail,
    summary="Buscar lead por ID",
)
async def get_lead(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await lead_service.get_lead(db, lead_id)


@router.patch(
    "/leads/{lead_id}/status",
    response_model=LeadDetail,
    summary="Atualizar status do lead",
)
async def update_lead_status(
    lead_id: uuid.UUID,
    data: LeadStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await lead_service.update_lead_status(db, lead_id, data)
