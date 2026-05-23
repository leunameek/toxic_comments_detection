from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..models.moderation import ModerationAction
from ..models.user import User

SCORE_RESET_THRESHOLD = 0.60
TIMEOUT_DURATION_SECONDS = 30


def _strikes_for_score(score: float) -> int:
    if score >= 0.90:
        return 3
    if score >= SCORE_RESET_THRESHOLD:
        return 1
    return 0


def _consequence(strikes: int) -> str | None:
    if strikes >= 8:
        return "BAN"
    if strikes >= 5:
        return "KICK"
    if strikes >= 3:
        return "TIMEOUT"
    if strikes >= 1:
        return "WARN"
    return None


def apply_strike(
    db: Session,
    user: User,
    score: float,
    message_id: str,
    session_id: str,
) -> ModerationAction | None:
    """
    Update the user's strike count based on message score and trigger the
    appropriate moderation action. Returns the created ModerationAction or None.
    """
    if score < 0.50:
        # Not toxic — no effect
        return None

    if score < SCORE_RESET_THRESHOLD:
        # Mild toxic: reset strikes, no action triggered
        user.strikes = 0
        db.flush()
        return None

    # Serious toxicity: accumulate strikes
    user.strikes += _strikes_for_score(score)
    consequence = _consequence(user.strikes)

    if not consequence:
        db.flush()
        return None

    reason = f"Accumulated {user.strikes} strike(s) — last message score {score:.2f}"
    duration = None

    if consequence == "BAN":
        user.status = "BANNED"
        user.timeout_until = None
    elif consequence == "KICK":
        # Kick: frontend removes player from session; status reflects severity
        user.status = "TIMEOUT"
        user.timeout_until = datetime.now(timezone.utc) + timedelta(
            seconds=TIMEOUT_DURATION_SECONDS * 6
        )
    elif consequence == "TIMEOUT":
        user.status = "TIMEOUT"
        user.timeout_until = datetime.now(timezone.utc) + timedelta(
            seconds=TIMEOUT_DURATION_SECONDS
        )
        duration = TIMEOUT_DURATION_SECONDS
    elif consequence == "WARN":
        user.status = "WARNED"

    action = ModerationAction(
        target_user_id=user.user_id,
        type=consequence,
        reason=reason,
        duration_seconds=duration,
        triggered_by="AUTO",
        message_id=message_id,
        session_id=session_id,
    )
    db.add(action)
    db.flush()
    return action
