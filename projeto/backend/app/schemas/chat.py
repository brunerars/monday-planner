import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChatStartRequest(BaseModel):
    lead_id: uuid.UUID = Field(..., examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"])


class ChatConfig(BaseModel):
    max_messages: int
    supports_audio: bool = False
    supports_image: bool = False
    supports_file: bool = False
    session_timeout_minutes: int


class ChatStartResponse(BaseModel):
    session_id: uuid.UUID
    lead_name: str
    lead_empresa: str
    greeting: str
    config: ChatConfig


class ChatMessageRequest(BaseModel):
    session_id: uuid.UUID
    content: str = Field(..., min_length=1, max_length=2000)


class SessionStatus(BaseModel):
    messages_used: int
    messages_remaining: int
    is_final: bool


class PlanTrigger(BaseModel):
    status: str
    estimated_seconds: int
    poll_url: str


class ChatMessageResponse(BaseModel):
    message_id: uuid.UUID
    response: str
    session_status: SessionStatus
    plan_trigger: Optional[PlanTrigger] = None


class ChatEndRequest(BaseModel):
    session_id: uuid.UUID
    reason: str = Field(default="user_requested")


class ChatEndResponse(BaseModel):
    session_id: uuid.UUID
    status: str
    plan_trigger: Optional[PlanTrigger] = None


class MessageItem(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    content_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatHistoryResponse(BaseModel):
    session_id: uuid.UUID
    lead_id: uuid.UUID
    status: str
    started_at: datetime
    ended_at: Optional[datetime]
    total_messages: int
    messages: list[MessageItem]

    model_config = {"from_attributes": True}
