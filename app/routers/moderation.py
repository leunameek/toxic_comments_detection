import base64
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..dependencies import get_db, require_moderator, KeyScope
from ..models import Message, ModerationAction, User
from ..schemas.common import APIResponse, PaginatedResult, ok
from ..schemas.moderation import (
    ModerationActionCreate, ModerationActionResponse, ModerationActionItem,
    QueueItem, QueueResult, ResolveRequest, ResolveResult,
)

router = APIRouter(prefix="/moderation", tags=["Moderation"])


def _get_message_or_404(db: Session, message_id: str) -> Message:
    msg = db.get(Message, message_id)
    if not msg:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": f"Message '{message_id}' not found"})
    return msg


@router.post("/actions", status_code=status.HTTP_201_CREATED, response_model=APIResponse[ModerationActionResponse])
def create_action(body: ModerationActionCreate, db: Session = Depends(get_db), scope: KeyScope = Depends(require_moderator)):
    user = db.get(User, body.target_user_id)
    if not user:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Target user not found"})

    action = ModerationAction(
        target_user_id=body.target_user_id,
        type=body.type,
        reason=body.reason,
        duration_seconds=body.duration_seconds,
        triggered_by="HUMAN",
        moderator_id=None,  # extracted from key in a real system
        message_id=body.message_id,
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return ok(ModerationActionResponse.model_validate(action))


@router.get("/actions", response_model=APIResponse[PaginatedResult[ModerationActionItem]])
def list_actions(
    user_id: str | None = Query(None),
    type: str | None = Query(None),
    triggered_by: str | None = Query(None),
    session_id: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
    db: Session = Depends(get_db),
    _scope=Depends(require_moderator),
):
    stmt = select(ModerationAction)
    if user_id:
        stmt = stmt.where(ModerationAction.target_user_id == user_id)
    if type:
        stmt = stmt.where(ModerationAction.type == type)
    if triggered_by:
        stmt = stmt.where(ModerationAction.triggered_by == triggered_by)
    if session_id:
        stmt = stmt.where(ModerationAction.session_id == session_id)
    if cursor:
        cursor_ts = datetime.fromisoformat(base64.b64decode(cursor).decode())
        stmt = stmt.where(ModerationAction.created_at < cursor_ts)

    stmt = stmt.order_by(ModerationAction.created_at.desc()).limit(limit + 1)
    rows = db.execute(stmt).scalars().all()

    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor = None
    if has_more:
        last_ts = items[-1].created_at.isoformat()
        next_cursor = base64.b64encode(last_ts.encode()).decode()

    return ok(PaginatedResult(
        items=[ModerationActionItem.model_validate(a) for a in items],
        next_cursor=next_cursor,
        has_more=has_more,
    ))


@router.get("/queue", response_model=APIResponse[QueueResult])
def get_queue(db: Session = Depends(get_db), _scope=Depends(require_moderator)):
    stmt = select(Message).where(Message.action == "REVIEW", Message.reviewed == False)
    rows = db.execute(stmt).scalars().all()
    items = [
        QueueItem(
            message_id=m.message_id,
            user_id=m.user_id,
            text=m.text,
            score=m.score or 0.0,
            action=m.action or "REVIEW",
            session_id=m.session_id,
            timestamp=m.timestamp,
        )
        for m in rows
    ]
    return ok(QueueResult(items=items, total=len(items)))


@router.post("/queue/{message_id}/resolve", response_model=APIResponse[ResolveResult])
def resolve_queue_item(
    message_id: str,
    body: ResolveRequest,
    db: Session = Depends(get_db),
    _scope=Depends(require_moderator),
):
    msg = _get_message_or_404(db, message_id)
    if msg.action != "REVIEW":
        raise HTTPException(status_code=409, detail={"code": "CONFLICT", "message": "Message is not in REVIEW state"})

    msg.reviewed = True
    now = datetime.now(timezone.utc)
    action_id = None

    if body.decision == "TOXIC" and body.action_type:
        action = ModerationAction(
            target_user_id=msg.user_id,
            type=body.action_type,
            reason=body.notes,
            triggered_by="HUMAN",
            message_id=message_id,
        )
        db.add(action)
        db.flush()
        action_id = action.action_id

    db.commit()
    return ok(ResolveResult(
        message_id=message_id,
        resolved_as=body.decision,
        action_created=action_id,
        resolved_by="moderator",
        resolved_at=now,
    ))
