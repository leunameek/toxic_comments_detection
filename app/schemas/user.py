from datetime import datetime
from pydantic import BaseModel


class UserProfile(BaseModel):
    user_id: str
    username: str
    toxicity_score: float
    total_messages: int
    toxic_messages: int
    strikes: int
    status: str
    timeout_until: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserStatusUpdate(BaseModel):
    status: str
    duration_seconds: int | None = None
    reason: str | None = None


class UserStatusResult(BaseModel):
    user_id: str
    status: str
    timeout_until: datetime | None


class MessageHistoryItem(BaseModel):
    message_id: str
    text: str
    label: int
    score: float
    action: str
    timestamp: datetime

    model_config = {"from_attributes": True}
