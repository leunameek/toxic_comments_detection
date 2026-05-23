from datetime import datetime
from pydantic import BaseModel


class TopToxicUser(BaseModel):
    user_id: str
    toxic_count: int
    avg_score: float


class SessionMetrics(BaseModel):
    session_id: str
    total_messages: int
    toxic_messages: int
    toxicity_rate: float
    avg_score: float
    peak_score: float
    actions_taken: dict[str, int]
    top_toxic_users: list[TopToxicUser]
    top_features: list[str]
    avg_latency_ms: float


class ModelMetrics(BaseModel):
    model_version: str
    total_classifications: int
    f1_score_online: float
    precision_online: float
    recall_online: float
    auc_roc: float
    avg_latency_ms: float
    human_corrections: int
    correction_rate: float
    loaded_at: datetime


class Period(BaseModel):
    from_: datetime
    to: datetime

    model_config = {"populate_by_name": True}


class ActionsSummary(BaseModel):
    AUTO_WARN: int = 0
    AUTO_TIMEOUT: int = 0
    AUTO_BLOCK: int = 0
    HUMAN_RESOLVED: int = 0


class GlobalMetrics(BaseModel):
    period: dict
    total_sessions: int
    total_messages: int
    toxicity_rate: float
    top_toxic_terms: list[str]
    actions_summary: ActionsSummary
