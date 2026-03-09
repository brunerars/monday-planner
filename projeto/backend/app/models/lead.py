import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Text, TIMESTAMP, Index, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tipo_negocio: Mapped[str] = mapped_column(String(3), nullable=False)
    segmento: Mapped[str] = mapped_column(String(100), nullable=False)
    empresa: Mapped[str] = mapped_column(String(200), nullable=False)
    porte: Mapped[str] = mapped_column(String(20), nullable=False)
    colaboradores: Mapped[Optional[str]] = mapped_column(String(50))
    cidade: Mapped[Optional[str]] = mapped_column(String(100))
    estado: Mapped[Optional[str]] = mapped_column(String(2))
    nome_contato: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    whatsapp: Mapped[Optional[str]] = mapped_column(String(20))
    cargo: Mapped[Optional[str]] = mapped_column(String(100))
    usa_monday: Mapped[Optional[str]] = mapped_column(String(20))
    areas_interesse: Mapped[Optional[list]] = mapped_column(JSONB)
    dor_principal: Mapped[Optional[str]] = mapped_column(Text)
    monday_item_id: Mapped[Optional[int]] = mapped_column(Integer)
    score: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="novo", index=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
