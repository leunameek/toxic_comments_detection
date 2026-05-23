from datetime import datetime
from pydantic import BaseModel, Field


class ClassifyRequest(BaseModel):
    message_id: str
    user_id: str
    session_id: str
    text: str = Field(..., max_length=500)
    timestamp: datetime | None = None


class ClassifyResult(BaseModel):
    message_id: str
    label: int
    score: float
    action: str
    top_features: list[str]
    processing_ms: float
    auto_action: str | None = None  # moderation consequence triggered (WARN/TIMEOUT/KICK/BAN)


class BatchClassifyRequest(BaseModel):
    messages: list[ClassifyRequest] = Field(..., max_length=50)


class BatchClassifyResult(BaseModel):
    results: list[ClassifyResult]
    total: int
    processing_ms: float
