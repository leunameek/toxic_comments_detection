from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..dependencies import get_db, require_player
from ..models import GameSession, Message
from ..schemas.common import APIResponse, ok
from ..schemas.session import (
    SessionCreate, SessionResponse, SessionDetail,
    SessionContextUpdate, SessionContextResult,
    SessionEndRequest, SessionEndResult,
)

router = APIRouter(prefix="/sessions", tags=["Sessions"])


def _get_session_or_404(db: Session, session_id: str) -> GameSession:
    s = db.get(GameSession, session_id)
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "NOT_FOUND", "message": f"Session '{session_id}' not found"})
    return s


@router.post("", status_code=status.HTTP_201_CREATED, response_model=APIResponse[SessionResponse])
def create_session(body: SessionCreate, db: Session = Depends(get_db), _scope=Depends(require_player)):
    if db.get(GameSession, body.session_id):
        raise HTTPException(status_code=409, detail={"code": "CONFLICT", "message": "Session already exists"})

    session = GameSession(
        session_id=body.session_id,
        match_type=body.match_type,
        players=body.players,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return ok(SessionResponse.model_validate(session))


@router.get("/{session_id}", response_model=APIResponse[SessionDetail])
def get_session(session_id: str, db: Session = Depends(get_db), _scope=Depends(require_player)):
    s = _get_session_or_404(db, session_id)

    message_count = db.execute(select(func.count()).where(Message.session_id == session_id)).scalar_one()
    toxic_count = db.execute(select(func.count()).where(Message.session_id == session_id, Message.label == 1)).scalar_one()

    duration = 0
    if s.created_at:
        end = s.ended_at or datetime.now(timezone.utc)
        duration = int((end - s.created_at).total_seconds())

    return ok(SessionDetail(
        session_id=s.session_id,
        match_type=s.match_type,
        status=s.status,
        context=s.context,
        duration_seconds=duration,
        players=s.players,
        message_count=message_count,
        toxic_count=toxic_count,
    ))


@router.patch("/{session_id}/context", response_model=APIResponse[SessionContextResult])
def update_context(session_id: str, body: SessionContextUpdate, db: Session = Depends(get_db), _scope=Depends(require_player)):
    allowed = {"WIN", "LOSS", "NEUTRAL"}
    if body.context not in allowed:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": f"context must be one of {allowed}"})

    s = _get_session_or_404(db, session_id)
    s.context = body.context
    db.commit()
    updated_at = datetime.now(timezone.utc)
    return ok(SessionContextResult(session_id=session_id, context=s.context, updated_at=updated_at))


@router.post("/{session_id}/end", response_model=APIResponse[SessionEndResult])
def end_session(session_id: str, body: SessionEndRequest, db: Session = Depends(get_db), _scope=Depends(require_player)):
    s = _get_session_or_404(db, session_id)

    now = datetime.now(timezone.utc)
    s.status = "FINISHED"
    s.ended_at = now
    if body.outcome in {"WIN", "LOSS", "NEUTRAL"}:
        s.context = body.outcome

    duration = int((now - s.created_at).total_seconds()) if s.created_at else 0
    total_msgs = db.execute(select(func.count()).where(Message.session_id == session_id)).scalar_one()
    toxic_msgs = db.execute(select(func.count()).where(Message.session_id == session_id, Message.label == 1)).scalar_one()

    db.commit()
    return ok(SessionEndResult(
        session_id=session_id,
        status="FINISHED",
        duration_seconds=duration,
        total_messages=total_msgs,
        toxic_messages=toxic_msgs,
        toxicity_rate=round(toxic_msgs / total_msgs, 4) if total_msgs else 0.0,
    ))
