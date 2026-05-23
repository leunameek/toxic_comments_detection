from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..dependencies import get_db, require_moderator, require_admin
from ..models import GameSession, Message, ModerationAction, User
from ..schemas.common import APIResponse, ok
from ..schemas.metrics import SessionMetrics, ModelMetrics, GlobalMetrics, TopToxicUser, ActionsSummary
from ..services import classifier

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/session/{session_id}", response_model=APIResponse[SessionMetrics])
def session_metrics(session_id: str, db: Session = Depends(get_db), _scope=Depends(require_moderator)):
    session = db.get(GameSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Session not found"})

    msgs = db.execute(select(Message).where(Message.session_id == session_id)).scalars().all()
    total = len(msgs)
    toxic = [m for m in msgs if m.label == 1]
    scores = [m.score for m in msgs if m.score is not None]
    latencies = [m.processing_ms for m in msgs if m.processing_ms is not None]

    actions_rows = db.execute(
        select(ModerationAction.type, func.count()).where(ModerationAction.session_id == session_id).group_by(ModerationAction.type)
    ).all()
    actions_taken = {row[0]: row[1] for row in actions_rows}

    # Top toxic users in this session
    user_toxic: dict[str, list[float]] = {}
    for m in toxic:
        user_toxic.setdefault(m.user_id, []).append(m.score or 0.0)
    top_toxic = sorted(
        [TopToxicUser(user_id=uid, toxic_count=len(sc), avg_score=round(sum(sc)/len(sc), 4)) for uid, sc in user_toxic.items()],
        key=lambda x: x.toxic_count, reverse=True,
    )[:5]

    # Top features across all messages in session
    feature_counts: dict[str, int] = {}
    for m in toxic:
        for f in (m.top_features or []):
            feature_counts[f] = feature_counts.get(f, 0) + 1
    top_features = sorted(feature_counts, key=feature_counts.get, reverse=True)[:10]

    return ok(SessionMetrics(
        session_id=session_id,
        total_messages=total,
        toxic_messages=len(toxic),
        toxicity_rate=round(len(toxic) / total, 4) if total else 0.0,
        avg_score=round(sum(scores) / len(scores), 4) if scores else 0.0,
        peak_score=round(max(scores), 4) if scores else 0.0,
        actions_taken=actions_taken,
        top_toxic_users=top_toxic,
        top_features=top_features,
        avg_latency_ms=round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
    ))


@router.get("/model", response_model=APIResponse[ModelMetrics])
def model_metrics(db: Session = Depends(get_db), _scope=Depends(require_admin)):
    stats = classifier.get_model_stats()

    human_corrections = db.execute(
        select(func.count()).where(ModerationAction.triggered_by == "HUMAN")
    ).scalar_one()

    total = stats["total_classifications"]
    correction_rate = round(human_corrections / total, 4) if total else 0.0

    return ok(ModelMetrics(
        model_version="svm_tfidf_v1",
        total_classifications=total,
        f1_score_online=0.0,
        precision_online=0.0,
        recall_online=0.0,
        auc_roc=0.0,
        avg_latency_ms=stats["avg_latency_ms"],
        human_corrections=human_corrections,
        correction_rate=correction_rate,
        loaded_at=stats["loaded_at"] or datetime.now(timezone.utc),
    ))


@router.get("/global", response_model=APIResponse[GlobalMetrics])
def global_metrics(
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
    db: Session = Depends(get_db),
    _scope=Depends(require_moderator),
):
    from_dt = datetime.fromisoformat(from_) if from_ else None
    to_dt = datetime.fromisoformat(to) if to else None

    msg_stmt = select(Message)
    if from_dt:
        msg_stmt = msg_stmt.where(Message.timestamp >= from_dt)
    if to_dt:
        msg_stmt = msg_stmt.where(Message.timestamp <= to_dt)
    msgs = db.execute(msg_stmt).scalars().all()

    total_sessions = db.execute(select(func.count()).select_from(GameSession)).scalar_one()
    total_msgs = len(msgs)
    toxic_msgs = [m for m in msgs if m.label == 1]

    feature_counts: dict[str, int] = {}
    for m in toxic_msgs:
        for f in (m.top_features or []):
            feature_counts[f] = feature_counts.get(f, 0) + 1
    top_terms = sorted(feature_counts, key=feature_counts.get, reverse=True)[:10]

    action_stmt = select(ModerationAction)
    actions = db.execute(action_stmt).scalars().all()
    summary = ActionsSummary(
        AUTO_WARN=sum(1 for a in actions if a.triggered_by == "AUTO" and a.type == "WARN"),
        AUTO_TIMEOUT=sum(1 for a in actions if a.triggered_by == "AUTO" and a.type == "TIMEOUT"),
        AUTO_BLOCK=sum(1 for a in actions if a.triggered_by == "AUTO" and a.type == "BLOCK"),
        HUMAN_RESOLVED=sum(1 for a in actions if a.triggered_by == "HUMAN"),
    )

    period = {
        "from": from_ or "all",
        "to": to or "all",
    }

    return ok(GlobalMetrics(
        period=period,
        total_sessions=total_sessions,
        total_messages=total_msgs,
        toxicity_rate=round(len(toxic_msgs) / total_msgs, 4) if total_msgs else 0.0,
        top_toxic_terms=top_terms,
        actions_summary=summary,
    ))
