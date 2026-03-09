import uuid
from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field, EmailStr, model_validator

_PORTES = {"MEI", "ME", "EPP", "Medio", "Grande"}
_COLABORADORES = {"1-5", "6-10", "11-50", "51-200", "201-500", "500+"}
_USA_MONDAY = {"sim", "nao", "avaliando"}
_AREAS = {"Vendas", "Projetos", "RH", "Financeiro", "Marketing", "Suporte", "Operacoes"}


class LeadCreate(BaseModel):
    tipo_negocio: str = Field(..., pattern="^(B2B|B2C)$", examples=["B2B"])
    segmento: str = Field(..., max_length=100, examples=["Tecnologia"])
    empresa: str = Field(..., max_length=200, examples=["Acme Ltda"])
    porte: str = Field(..., examples=["ME"])
    colaboradores: Optional[str] = Field(None, examples=["11-50"])
    cidade: Optional[str] = Field(None, max_length=100, examples=["São Paulo"])
    estado: Optional[str] = Field(None, min_length=2, max_length=2, examples=["SP"])
    nome_contato: str = Field(..., max_length=200, examples=["João Silva"])
    email: EmailStr = Field(..., examples=["joao@acme.com.br"])
    whatsapp: Optional[str] = Field(None, max_length=20, examples=["11999999999"])
    cargo: Optional[str] = Field(None, max_length=100, examples=["Diretor de Operações"])
    usa_monday: Optional[str] = Field(None, examples=["avaliando"])
    areas_interesse: list[str] = Field(..., min_length=1, examples=[["Vendas", "Projetos"]])
    dor_principal: Optional[str] = Field(None, max_length=280, examples=["Processos manuais"])

    @model_validator(mode="after")
    def validate_enums(self) -> "LeadCreate":
        if self.porte not in _PORTES:
            raise ValueError(f"porte deve ser um de: {sorted(_PORTES)}")
        if self.colaboradores and self.colaboradores not in _COLABORADORES:
            raise ValueError(f"colaboradores deve ser um de: {sorted(_COLABORADORES)}")
        if self.usa_monday and self.usa_monday not in _USA_MONDAY:
            raise ValueError(f"usa_monday deve ser um de: {sorted(_USA_MONDAY)}")
        areas_invalidas = set(self.areas_interesse) - _AREAS
        if areas_invalidas:
            raise ValueError(f"Áreas inválidas: {areas_invalidas}. Válidas: {sorted(_AREAS)}")
        return self


class LeadResponse(BaseModel):
    id: uuid.UUID
    empresa: str
    nome_contato: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LeadDetail(BaseModel):
    id: uuid.UUID
    tipo_negocio: str
    segmento: str
    empresa: str
    porte: str
    colaboradores: Optional[str]
    cidade: Optional[str]
    estado: Optional[str]
    nome_contato: str
    email: str
    whatsapp: Optional[str]
    cargo: Optional[str]
    usa_monday: Optional[str]
    areas_interesse: Optional[list[str]]
    dor_principal: Optional[str]
    score: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PartialLeadCreate(BaseModel):
    step_completed: int = Field(..., ge=1, le=4)
    data: dict[str, Any]


class PartialLeadResponse(BaseModel):
    id: str
    step_completed: int
    recoverable: bool


class LeadStatusUpdate(BaseModel):
    status: str = Field(..., examples=["call_agendada"])
