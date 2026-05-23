from datetime import datetime
from pydantic import BaseModel


class SessionCreate(BaseModel):
    session_id: str
    match_type: str
    players: list[str]


class SessionResponse(BaseModel):
    session_id: str
    status: str
    context: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionDetail(BaseModel):
    session_id: str
    match_type: str
    status: str
    context: str
    duration_seconds: int
    players: list[str]
    message_count: int
    toxic_count: int

    model_config = {"from_attributes": True}


class SessionContextUpdate(BaseModel):
    context: str


class SessionContextResult(BaseModel):
    session_id: str
    context: str
    updated_at: datetime


class SessionEndRequest(BaseModel):
    outcome: str


class SessionEndResult(BaseModel):
    session_id: str
    status: str
    duration_seconds: int
    total_messages: int
    toxic_messages: int
    toxicity_rate: float
