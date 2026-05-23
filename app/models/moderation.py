import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class ModerationAction(Base):
    __tablename__ = "moderation_actions"

    action_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"act_{uuid.uuid4().hex[:8]}")
    target_user_id: Mapped[str] = mapped_column(String, ForeignKey("users.user_id"), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    triggered_by: Mapped[str] = mapped_column(String, nullable=False)
    moderator_id: Mapped[str | None] = mapped_column(String, nullable=True)
    message_id: Mapped[str | None] = mapped_column(String, ForeignKey("messages.message_id"), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    target_user: Mapped["User"] = relationship("User", back_populates="moderation_actions")
