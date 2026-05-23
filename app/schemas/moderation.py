from datetime import datetime
from pydantic import BaseModel


class ModerationActionCreate(BaseModel):
    target_user_id: str
    type: str
    reason: str | None = None
    duration_seconds: int | None = None
    message_id: str | None = None


class ModerationActionResponse(BaseModel):
    action_id: str
    target_user_id: str
    type: str
    triggered_by: str
    moderator_id: str | None
    duration_seconds: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ModerationActionItem(BaseModel):
    action_id: str
    target_user_id: str
    type: str
    reason: str | None
    triggered_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


class QueueItem(BaseModel):
    message_id: str
    user_id: str
    text: str
    score: float
    action: str
    session_id: str
    timestamp: datetime

    model_config = {"from_attributes": True}


class QueueResult(BaseModel):
    items: list[QueueItem]
    total: int


class ResolveRequest(BaseModel):
    decision: str
    action_type: str | None = None
    notes: str | None = None


class ResolveResult(BaseModel):
    message_id: str
    resolved_as: str
    action_created: str | None
    resolved_by: str
    resolved_at: datetime
