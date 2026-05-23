from datetime import datetime, timezone
from typing import Generic, TypeVar
from pydantic import BaseModel, field_serializer

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict | None = None


class APIResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None
    error: ErrorDetail | None = None
    timestamp: datetime = None  # type: ignore[assignment]

    def model_post_init(self, __context):
        if self.timestamp is None:
            object.__setattr__(self, "timestamp", datetime.now(timezone.utc))

    @field_serializer("timestamp")
    def serialize_timestamp(self, v: datetime) -> str:
        return v.strftime("%Y-%m-%dT%H:%M:%SZ")


def ok(data: T) -> APIResponse[T]:
    return APIResponse(success=True, data=data)


def err(code: str, message: str, details: dict | None = None) -> APIResponse[None]:
    return APIResponse(success=False, data=None, error=ErrorDetail(code=code, message=message, details=details))


class PaginatedResult(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None
    has_more: bool = False
