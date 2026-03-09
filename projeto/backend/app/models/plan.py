import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Text, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id")
    )
    # Desnormalizado para facilitar responses e download sem join
    empresa: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    content_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    summary_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    version: Mapped[int] = mapped_column(Integer, default=1)
    # status: generating | generated | error
    status: Mapped[str] = mapped_column(String(20), default="generating")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
