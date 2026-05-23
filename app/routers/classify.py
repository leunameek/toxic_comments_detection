import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..dependencies import get_db, require_player
from ..models import Message, User
from ..schemas.classify import ClassifyRequest, ClassifyResult, BatchClassifyRequest, BatchClassifyResult
from ..schemas.common import APIResponse, ok
from ..services import classifier
from ..services.moderation_service import apply_strike

router = APIRouter(prefix="/classify", tags=["Classification"])


def _ensure_user(db: Session, user_id: str) -> User:
    user = db.get(User, user_id)
    if not user:
        user = User(user_id=user_id, username=user_id)
        db.add(user)
        db.flush()
    return user


def _classify_one(db: Session, req: ClassifyRequest) -> ClassifyResult:
    # Idempotency: return cached result for same message_id
    cached = db.get(Message, req.message_id)
    if cached and cached.label is not None:
        return ClassifyResult(
            message_id=cached.message_id,
            label=cached.label,
            score=cached.score,
            action=cached.action,
            top_features=cached.top_features or [],
            processing_ms=cached.processing_ms or 0.0,
        )

    if not classifier.is_model_loaded():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"code": "MODEL_UNAVAILABLE", "message": "ML pipeline not loaded"})

    user = _ensure_user(db, req.user_id)

    # Banned users are blocked immediately without inference
    if user.status == "BANNED":
        result = ClassifyResult(
            message_id=req.message_id,
            label=1,
            score=1.0,
            action="BLOCK",
            top_features=[],
            processing_ms=0.0,
        )
    else:
        if not req.text.strip():
            raise HTTPException(status_code=422, detail={"code": "UNPROCESSABLE", "message": "Text is empty after preprocessing"})

        prediction = classifier.predict(req.text)
        result = ClassifyResult(message_id=req.message_id, **prediction)

    ts = req.timestamp or datetime.now(timezone.utc)
    msg = cached or Message(message_id=req.message_id)
    msg.session_id = req.session_id
    msg.user_id = req.user_id
    msg.text = req.text
    msg.timestamp = ts
    msg.label = result.label
    msg.score = result.score
    msg.action = result.action
    msg.top_features = result.top_features
    msg.processing_ms = result.processing_ms

    if not cached:
        db.add(msg)

    # Update user counters
    user.total_messages += 1
    if result.label == 1:
        user.toxic_messages += 1
        user.toxicity_score = round(0.9 * user.toxicity_score + 0.1 * result.score, 4)

    # Apply strike logic and auto-moderation (skipped for already-banned users)
    auto_action = None
    if user.status != "BANNED" and result.label == 1:
        mod = apply_strike(db, user, result.score, req.message_id, req.session_id)
        if mod:
            auto_action = mod.type

    db.commit()
    return result.model_copy(update={"auto_action": auto_action})


@router.post("", response_model=APIResponse[ClassifyResult])
def classify(req: ClassifyRequest, db: Session = Depends(get_db), _scope=Depends(require_player)):
    result = _classify_one(db, req)
    return ok(result)


@router.post("/batch", response_model=APIResponse[BatchClassifyResult])
def classify_batch(req: BatchClassifyRequest, db: Session = Depends(get_db), _scope=Depends(require_player)):
    t0 = time.perf_counter()
    results = [_classify_one(db, msg) for msg in req.messages]
    total_ms = round((time.perf_counter() - t0) * 1000, 2)
    return ok(BatchClassifyResult(results=results, total=len(results), processing_ms=total_ms))
