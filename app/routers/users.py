import base64
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..dependencies import get_db, require_player, require_moderator
from ..models import User, Message
from ..schemas.common import APIResponse, PaginatedResult, ok
from ..schemas.user import UserProfile, UserStatusUpdate, UserStatusResult, MessageHistoryItem

router = APIRouter(prefix="/users", tags=["Users"])


def _get_user_or_404(db: Session, user_id: str) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "NOT_FOUND", "message": f"User '{user_id}' not found"})
    return user


@router.get("/{user_id}", response_model=APIResponse[UserProfile])
def get_user(user_id: str, db: Session = Depends(get_db), _scope=Depends(require_player)):
    user = _get_user_or_404(db, user_id)
    return ok(UserProfile.model_validate(user))


@router.get("/{user_id}/history", response_model=APIResponse[PaginatedResult[MessageHistoryItem]])
def get_user_history(
    user_id: str,
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
    only_toxic: bool = Query(False),
    session_id: str | None = Query(None),
    db: Session = Depends(get_db),
    _scope=Depends(require_player),
):
    _get_user_or_404(db, user_id)

    stmt = select(Message).where(Message.user_id == user_id)

    if only_toxic:
        stmt = stmt.where(Message.label == 1)
    if session_id:
        stmt = stmt.where(Message.session_id == session_id)

    if cursor:
        cursor_ts = datetime.fromisoformat(base64.b64decode(cursor).decode())
        stmt = stmt.where(Message.timestamp < cursor_ts)

    stmt = stmt.order_by(Message.timestamp.desc()).limit(limit + 1)
    rows = db.execute(stmt).scalars().all()

    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor = None
    if has_more:
        last_ts = items[-1].timestamp.isoformat()
        next_cursor = base64.b64encode(last_ts.encode()).decode()

    return ok(PaginatedResult(
        items=[MessageHistoryItem.model_validate(m) for m in items],
        next_cursor=next_cursor,
        has_more=has_more,
    ))


@router.put("/{user_id}/status", response_model=APIResponse[UserStatusResult])
def update_user_status(user_id: str, body: UserStatusUpdate, db: Session = Depends(get_db), _scope=Depends(require_moderator)):
    user = _get_user_or_404(db, user_id)

    allowed = {"ACTIVE", "WARNED", "TIMEOUT", "BANNED"}
    if body.status not in allowed:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": f"status must be one of {allowed}"})

    user.status = body.status
    timeout_until = None
    if body.status == "TIMEOUT" and body.duration_seconds:
        timeout_until = datetime.now(timezone.utc) + timedelta(seconds=body.duration_seconds)
        user.timeout_until = timeout_until
    else:
        user.timeout_until = None

    db.commit()
    return ok(UserStatusResult(user_id=user_id, status=user.status, timeout_until=timeout_until))
