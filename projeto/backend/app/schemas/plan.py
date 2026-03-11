import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, model_validator


class PlanSummary(BaseModel):
    boards: Optional[int] = None
    automacoes_make: Optional[int] = None
    automacoes_n8n: Optional[int] = None
    agentes_ia: Optional[int] = None
    integracoes: Optional[int] = None
    plano_recomendado: Optional[str] = None
    usuarios_estimados: Optional[int] = None
    custo_mensal_estimado_brl: Optional[float] = None
    fases_implementacao: Optional[int] = None
    semanas_estimadas: Optional[int] = None


class PlanStatusResponse(BaseModel):
    plan_id: uuid.UUID
    status: str
    progress_percent: Optional[int] = None
    estimated_seconds_remaining: Optional[int] = None
    plan_url: Optional[str] = None
    download_url: Optional[str] = None
    message: Optional[str] = None


class PlanResponse(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    empresa: str
    version: int
    status: str
    content_md: str
    summary: Optional[PlanSummary] = None
    created_at: datetime
    download_url: str
    cta_url: str

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def populate_summary(cls, data):
        """Mapeia summary_json (modelo ORM) → summary (schema)."""
        if hasattr(data, "summary_json") and data.summary_json:
            object.__setattr__(data, "_summary_parsed", data.summary_json)
        return data
